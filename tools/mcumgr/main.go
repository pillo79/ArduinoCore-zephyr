/*
 * Copyright (c) 2026 RAKwireless Technology Limited
 * SPDX-License-Identifier: Apache-2.0
 */

/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *  http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

/**
 * This file mirrors mcumgr/mcumgr.go from github.com/apache/mynewt-mcumgr-cli
 * (Apache-2.0) on top of the same newtmgr libraries.
 */

package main

import (
	"bytes"
	"encoding/binary"
	"errors"
	"fmt"
	"io/ioutil"
	"os"
	"os/signal"
	"syscall"

	"github.com/spf13/cobra"
	"mynewt.apache.org/newt/util"
	"mynewt.apache.org/newtmgr/newtmgr/cli"
	"mynewt.apache.org/newtmgr/newtmgr/config"
	"mynewt.apache.org/newtmgr/newtmgr/nmutil"
	"mynewt.apache.org/newtmgr/nmxact/nmserial"
	"mynewt.apache.org/newtmgr/nmxact/xact"
)

func stopXport() {
	x, err := cli.GetXportIfOpen()
	if err == nil {
		// Don't attempt to close a serial transport.  Attempting to close
		// the serial port while a read is in progress (in MacOS) just
		// blocks until the read completes.  Instead, let the OS close the
		// port on termination.
		if _, ok := x.(*nmserial.SerialXport); !ok {
			x.Stop()
		}
	}
}

func closeSesn() {
	s, err := cli.GetSesnIfOpen()
	if err == nil {
		s.Close()
	}
}

func cleanup() {
	closeSesn()
	stopXport()
}

// imageHash returns the SHA-256 of an MCUboot image, as stored in the
// unprotected TLV area that follows the header, the payload and the
// protected TLVs.
func imageHash(data []byte) ([]byte, error) {
	const (
		imageMagic   = 0x96f3b83d
		tlvInfoMagic = 0x6907
		tlvSHA256    = 0x10
	)

	if len(data) < 32 || binary.LittleEndian.Uint32(data) != imageMagic {
		return nil, errors.New("not an MCUboot image")
	}
	hdrSize := int(binary.LittleEndian.Uint16(data[8:]))
	protSize := int(binary.LittleEndian.Uint16(data[10:]))
	imgSize := int(binary.LittleEndian.Uint32(data[12:]))

	off := hdrSize + imgSize + protSize
	if off+4 > len(data) || binary.LittleEndian.Uint16(data[off:]) != tlvInfoMagic {
		return nil, errors.New("no TLV area")
	}
	end := off + int(binary.LittleEndian.Uint16(data[off+2:]))
	if end > len(data) {
		return nil, errors.New("truncated TLV area")
	}
	for p := off + 4; p+4 <= end; {
		typ := binary.LittleEndian.Uint16(data[p:])
		size := int(binary.LittleEndian.Uint16(data[p+2:]))
		if p+4+size > end {
			break
		}
		if typ == tlvSHA256 {
			return data[p+4 : p+4+size], nil
		}
		p += 4 + size
	}
	return nil, errors.New("no SHA-256 TLV")
}

// imageOnBoard reports whether a slot of the board already holds the image
// in path. Failing to open the connection is an error, as for the upload
// itself (newtmgr keeps the unopened session, which the upload cannot use);
// any other failure (not an MCUboot image, no answer) means the board does
// not hold the image, so it is uploaded.
func imageOnBoard(path string) (bool, error) {
	data, err := ioutil.ReadFile(path)
	if err != nil {
		return false, nil
	}
	hash, err := imageHash(data)
	if err != nil {
		return false, nil
	}

	s, err := cli.GetSesn()
	if err != nil {
		return false, err
	}
	c := xact.NewImageStateReadCmd()
	c.SetTxOptions(nmutil.TxOptions())
	res, err := c.Run(s)
	if err != nil {
		return false, nil
	}
	for _, img := range res.(*xact.ImageStateReadResult).Rsp.Images {
		if bytes.Equal(img.Hash, hash) {
			return true, nil
		}
	}
	return false, nil
}

// addSkipSame adds --skip-same to "image upload": the upload is skipped if
// the board already holds the same image, so the loader is only sent when
// it changed.
func addSkipSame(root *cobra.Command) {
	upload, _, err := root.Find([]string{"image", "upload"})
	if err != nil || upload.Name() != "upload" {
		panic("mcumgr: no image upload command")
	}

	var skipSame bool
	upload.PersistentFlags().BoolVar(&skipSame, "skip-same", false,
		"Skip the upload if a slot of the device already holds this image (same SHA-256)")

	run := upload.Run
	upload.Run = func(cmd *cobra.Command, args []string) {
		if skipSame && len(args) > 0 {
			same, err := imageOnBoard(args[0])
			if err != nil {
				fmt.Fprintf(os.Stderr, "Error: %s\n", err.Error())
				cli.NmExit(1)
			}
			if same {
				fmt.Println("Same image already on the device, upload skipped")
				return
			}
		}
		run(cmd, args)
	}
}

func main() {
	nmutil.ToolInfo = nmutil.ToolInfoType{
		ExeName:       "mcumgr",
		ShortName:     "mcumgr",
		LongName:      "mcumgr",
		VersionString: "0.0.0-dev",
		CfgFilename:   ".mcumgr.cp.json",
	}

	if err := config.InitGlobalConnProfileMgr(); err != nil {
		fmt.Fprintf(os.Stderr, "Error: %s\n", err.Error())
		os.Exit(1)
	}

	defer cleanup()
	cli.SetOnExit(cleanup)

	sigChan := make(chan os.Signal, 1)
	signal.Notify(sigChan)

	go func() {
		for {
			s := <-sigChan
			switch s {
			case os.Interrupt, syscall.SIGTERM:
				cli.SilenceErrors()
				cli.NmExit(1)

			case syscall.SIGQUIT:
				util.PrintStacks()
			}
		}
	}()

	root := cli.Commands()
	addSkipSame(root)
	root.Execute()
}
