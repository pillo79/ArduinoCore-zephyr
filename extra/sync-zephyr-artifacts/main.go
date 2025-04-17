// SPDX-License-Identifier: MPL-2.0
// Copyright (C) 2025 Arduino SA

package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"strings"

	"github.com/codeclysm/extract/v4"
	"github.com/go-git/go-git/v5"
)

func downloadFile(filepath string, url string) (err error) {

	// Create the file
	out, err := os.Create(filepath)
	if err != nil {
		return err
	}
	defer out.Close()

	// Get the data
	resp, err := http.Get(url)
	if err != nil {
		return err
	}
	defer resp.Body.Close()

	// Check server response
	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("bad status: %s", resp.Status)
	}

	// Writer the body to file
	_, err = io.Copy(out, resp.Body)
	if err != nil {
		return err
	}

	return nil
}

func main() {

	// Create a temporary folder, download a URL based on a git tag in it
	// and extract the zip file to the temporary folder
	tmpDir, err := os.MkdirTemp("", "sync_zephyr_artifacts")
	if err != nil {
		fmt.Println("Error creating temp dir:", err)
		return
	}
	defer os.RemoveAll(tmpDir) // Clean up

	// Download the zip file from http://downloads.arduino.cc/cores/zephyr/zephyr-core-llext-{git_tag}.zip
	// and save it to zipFilePath
	// Replace {git_tag} with the actual git tag

	gitCorePath := os.Args[1]
	// Force an hash, for debug only
	forceHash := ""
	if len(os.Args) > 2 {
		forceHash = os.Args[2]
	}
	r, err := git.PlainOpen(gitCorePath)
	if err != nil {
		fmt.Println("Error opening git repository:", err)
		return
	}
	ref, err := r.Head()
	if err != nil {
		fmt.Println("Error getting git reference:", err)
		return
	}
	w, err := r.Worktree()
	if err != nil {
		fmt.Println("Error getting git worktree:", err)
		return
	}
	// Check if the repo contains modifications in either variants or firmwares folders
	status, err := w.StatusWithOptions(git.StatusOptions{Strategy: git.Preload})
	if err != nil {
		fmt.Println("Error getting git status:", err)
		return
	}
	if !status.IsClean() {
		// Check if there are untracked/modified files in the firmwares or variants folders
		for path, s := range status {
			if strings.HasPrefix(path, "firmwares/") || strings.HasPrefix(path, "variants/") {
				fmt.Println("The git repository contains uncommitted changes in", path)
				if s.Worktree != git.Untracked {
					fmt.Println("Please stash them before running this script.")
				}
				return
			}
		}
	}
	fmt.Println("Git tag:", ref.Hash())
	// Replace {git_tag} with the actual git tag in the URL
	hash := ref.Hash().String()[0:7]
	if forceHash != "" {
		hash = forceHash
	}
	filename := fmt.Sprintf("arduino-core-zephyr-llext-%s.tar.bz2", hash)
	url := fmt.Sprintf("http://downloads.arduino.cc/cores/zephyr/%s", filename)
	fmt.Println("Download URL:", url)
	// Download the zip file from the URL
	zipFilePath := filepath.Join(tmpDir, filename)
	err = downloadFile(zipFilePath, url)
	if err != nil {
		fmt.Println("Error downloading zip file:", err)
		return
	}
	fmt.Println("Downloaded zip file to:", zipFilePath)
	// Extract the tar.bz2 file to the temporary folder
	// Use packer/tar and compress/bzip2 to extract the file
	file, err := os.Open(filepath.Join(tmpDir, filename))
	if err != nil {
		fmt.Println("Error opening zip file:", err)
		return
	}
	defer file.Close()
	extract.Bz2(context.Background(), file, filepath.Join(tmpDir, "extract"), nil)
	// Copy the content of firmware folder to gitCorePath/firmware
	err = os.CopyFS(filepath.Join(gitCorePath, "firmwares"), os.DirFS(filepath.Join(tmpDir, "extract", "ArduinoCore-zephyr", "firmwares")))
	if err != nil {
		fmt.Println("Error copying firmware folder:", err)
		return
	}
	// Copy the content of variants folder to gitCorePath/variants
	// Since CopyFS does not overwrite, before doing so remove gitCorePath/variants
	// TODO: make sure there's no outstanding change in gitCorePath/variants
	// Bail out in that case with a clear error message
	err = os.RemoveAll(filepath.Join(gitCorePath, "variants"))
	if err != nil {
		fmt.Println("Error renaming variants folder:", err)
		return
	}
	err = os.CopyFS(filepath.Join(gitCorePath, "variants"), os.DirFS(filepath.Join(tmpDir, "extract", "ArduinoCore-zephyr", "variants")))
	if err != nil {
		fmt.Println("Error copying variants folder:", err)
		return
	}
}
