#!/bin/bash

# Configuration
ROOT_DIR="/home/z/my-project/mini-services"

main() {
    echo "Starting batch dependency installation..."
    
    if [ ! -d "$ROOT_DIR" ]; then
        echo "Directory $ROOT_DIR does not exist, skipping installation"
        return
    fi
    
    success_count=0
    fail_count=0
    failed_projects=""
    
    for dir in "$ROOT_DIR"/*; do
        if [ -d "$dir" ] && [ -f "$dir/package.json" ]; then
            project_name=$(basename "$dir")
            echo ""
            echo "Installing dependencies: $project_name..."
            
            if (cd "$dir" && bun install); then
                echo "SUCCESS: $project_name dependencies installed"
                success_count=$((success_count + 1))
            else
                echo "FAILED: $project_name dependency installation failed"
                fail_count=$((fail_count + 1))
                if [ -z "$failed_projects" ]; then
                    failed_projects="$project_name"
                else
                    failed_projects="$failed_projects $project_name"
                fi
            fi
        fi
    done
    
    echo ""
    echo "=================================================="
    if [ $success_count -gt 0 ] || [ $fail_count -gt 0 ]; then
        echo "Installation complete!"
        echo "Succeeded: $success_count"
        if [ $fail_count -gt 0 ]; then
            echo "Failed: $fail_count"
            echo ""
            echo "Failed projects:"
            for project in $failed_projects; do
                echo "  - $project"
            done
        fi
    else
        echo "No projects with package.json found"
    fi
    echo "=================================================="
}

main
