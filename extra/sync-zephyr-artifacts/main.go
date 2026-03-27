// SPDX-License-Identifier: MPL-2.0
// Copyright (c) Arduino s.r.l. and/or its affiliated companies

package main

import (
	"context"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	"github.com/codeclysm/extract/v4"
	cp "github.com/otiai10/copy"
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
	// and extract the file to the temporary folder
	tmpDir, err := os.MkdirTemp("", "sync-zephyr-artifacts")
	if err != nil {
		fmt.Println("Error creating temp dir:", err)
		return
	}
	defer os.RemoveAll(tmpDir) // Clean up

	// usage: sync-zephyr-artifacts [<git_core_path>] [forced_hash]

	// parse arguments
	if len(os.Args) > 1 && (os.Args[1] == "-h" || os.Args[1] == "--help") {
		fmt.Fprintf(os.Stderr, "Usage: %s [<git_core_path>] [forced_hash]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "  git_core_path: path to the ArduinoCore-zephyr git repository (default: current directory)\n")
		fmt.Fprintf(os.Stderr, "  forced_hash:   force a specific git hash (for debug only)\n")
		os.Exit(0)
	}

	// Download the file from http://downloads.arduino.cc/cores/zephyr/ArduinoCore-zephyr-{git_tag}.zip
	gitCorePath := "."
	if len(os.Args) > 1 {
		gitCorePath = os.Args[1]
	}

	// Force a specific hash, for debug only
	inputHash := ""
	if len(os.Args) > 2 {
		inputHash = os.Args[2]
	}

	// Test if the provided path contains 'variants/' folder
	if _, err := os.Stat(filepath.Join(gitCorePath, "variants")); os.IsNotExist(err) {
		fmt.Println("Error: not an ArduinoCore-zephyr folder:", gitCorePath)
		return
	}

	if inputHash == "" {
		cmd := exec.Command("git", "-C", gitCorePath, "describe", "--always", "HEAD")
		stdout, err := cmd.Output()
		if err != nil {
			fmt.Println("Error executing command:", err)
			return
		}

		inputHash = strings.TrimSpace(string(stdout))
	}
	fmt.Println("Git SHA:", inputHash)

	cmd := exec.Command("git", "ls-files", "--exclude-standard", "-dmo", gitCorePath)
	stdout, err := cmd.Output()
	if err != nil {
		fmt.Println("Error executing command:", err)
		return
	}

	var lines []string
	var changes []string
	lines = strings.Split(string(stdout), "\n")
	for _, path := range lines {
		if strings.HasPrefix(path, "firmwares/") || strings.HasPrefix(path, "variants/") {
			changes = append(changes, path)
		}
	}

	if len(changes) > 0 {
		fmt.Println("The git repository contains uncommitted files:")
		for _, path := range changes {
			fmt.Println("- ", path)
		}
		fmt.Println("Please commit or stash them before running this script.")
		return
	}

	// Compose download URL from git hash
	hash := inputHash
	filename := fmt.Sprintf("ArduinoCore-zephyr-%s.tar.bz2", hash)
	url := fmt.Sprintf("http://downloads.arduino.cc/cores/zephyr/%s", filename)
	fmt.Println("Download URL:", url)
	// Download the zip file from the URL
	zipFilePath := filepath.Join(tmpDir, filename)
	err = downloadFile(zipFilePath, url)
	if err != nil {
		fmt.Println("Error downloading archive:", err)
		return
	}
	fmt.Println("Downloaded archive to:", zipFilePath)
	// Extract the tar.bz2 file to the temporary folder
	// Use packer/tar and compress/bzip2 to extract the file
	file, err := os.Open(filepath.Join(tmpDir, filename))
	if err != nil {
		fmt.Println("Error opening archive:", err)
		return
	}
	defer file.Close()

	err = extract.Bz2(context.Background(), file, filepath.Join(tmpDir, "extract"), nil)
	if err != nil {
		fmt.Println("Error extracting archive:", err)
		return
	}

	// Remove old firmwares and variants/*/llext-edk files
	os.RemoveAll(filepath.Join(gitCorePath, "firmwares"))
	filepath.WalkDir(filepath.Join(gitCorePath, "variants"), func(path string, d os.DirEntry, err error) error {
		if err != nil {
			fmt.Println("Error:", err)
			return nil
		}

		if d.IsDir() && d.Name() == "llext-edk" {
			os.RemoveAll(path)
		}
		return nil
	})

	// Copy the content of firmware folder to gitCorePath/firmware
	err = cp.Copy(filepath.Join(tmpDir, "extract", "ArduinoCore-zephyr", "firmwares"), filepath.Join(gitCorePath, "firmwares"))
	if err != nil {
		fmt.Println("Error copying firmware folder:", err)
		return
	}
	// Copy the content of variants folder to gitCorePath/variants
	err = cp.Copy(filepath.Join(tmpDir, "extract", "ArduinoCore-zephyr", "variants"), filepath.Join(gitCorePath, "variants"))
	if err != nil {
		fmt.Println("Error copying variants folder:", err)
		return
	}

	fmt.Println("Done.")
}
