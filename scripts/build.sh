#!/bin/bash

# Redirect stderr to stdout
exec 2>&1

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Next.js project path
NEXTJS_PROJECT_DIR="/home/z/my-project"

# Check if Next.js project directory exists
if [ ! -d "$NEXTJS_PROJECT_DIR" ]; then
    echo "ERROR: Next.js project directory does not exist: $NEXTJS_PROJECT_DIR"
    exit 1
fi

echo "Starting Next.js build..."
echo "Project path: $NEXTJS_PROJECT_DIR"

# Switch to project directory
cd "$NEXTJS_PROJECT_DIR" || exit 1

# Set environment variables
export NEXT_TELEMETRY_DISABLED=1

BUILD_DIR="/tmp/build_fullstack_$BUILD_ID"
echo "Creating build directory: $BUILD_DIR"
mkdir -p "$BUILD_DIR"

# Install dependencies
echo "Installing dependencies..."
bun install

# Build Next.js application
echo "Building Next.js application..."
bun run build

# Build mini-services (if directory exists)
if [ -d "$NEXTJS_PROJECT_DIR/mini-services" ]; then
    echo "Building mini-services..."
    sh "$SCRIPT_DIR/mini-services-install.sh"
    sh "$SCRIPT_DIR/mini-services-build.sh"

    echo "Copying mini-services-start.sh to $BUILD_DIR"
    cp "$SCRIPT_DIR/mini-services-start.sh" "$BUILD_DIR/mini-services-start.sh"
    chmod +x "$BUILD_DIR/mini-services-start.sh"
else
    echo "mini-services directory not found, skipping"
fi

# Copy build output to build directory
echo "Collecting build artifacts to $BUILD_DIR..."

# Copy Next.js standalone build output
if [ -d ".next/standalone" ]; then
    echo "  - Copying .next/standalone"
    cp -r .next/standalone "$BUILD_DIR/next-service-dist/"
fi

# Copy Next.js static files
if [ -d ".next/static" ]; then
    echo "  - Copying .next/static"
    mkdir -p "$BUILD_DIR/next-service-dist/.next"
    cp -r .next/static "$BUILD_DIR/next-service-dist/.next/"
fi

# Copy public directory
if [ -d "public" ]; then
    echo "  - Copying public"
    cp -r public "$BUILD_DIR/next-service-dist/"
fi

# Copy database file to build output
if [ -f "./db/custom.db" ]; then
    echo "Copying database to build output..."
    mkdir -p "$BUILD_DIR/db"
    cp -r ./db/. "$BUILD_DIR/db/"

    echo "Syncing database schema..."
    DATABASE_URL="file:$BUILD_DIR/db/custom.db" bun run db:push
    echo "Database preparation complete"
    ls -lah "$BUILD_DIR/db"
else
    echo "ERROR: Database file ./db/custom.db not found, cannot continue"
    exit 1
fi

# Copy Caddyfile (if exists)
if [ -f "Caddyfile" ]; then
    echo "  - Copying Caddyfile"
    cp Caddyfile "$BUILD_DIR/"
else
    echo "Caddyfile not found, skipping"
fi

# Copy start.sh script
echo "  - Copying start.sh to $BUILD_DIR"
cp "$SCRIPT_DIR/start.sh" "$BUILD_DIR/start.sh"
chmod +x "$BUILD_DIR/start.sh"

# Package into tar.gz
PACKAGE_FILE="${BUILD_DIR}.tar.gz"
echo ""
echo "Packaging build artifacts to $PACKAGE_FILE..."
cd "$BUILD_DIR" || exit 1
tar -czf "$PACKAGE_FILE" .
cd - > /dev/null || exit 1

echo ""
echo "Build complete! All artifacts packaged to $PACKAGE_FILE"
echo "Package size:"
ls -lh "$PACKAGE_FILE"
