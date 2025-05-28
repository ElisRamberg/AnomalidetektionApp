#!/bin/bash

# Script to fix React dependency conflicts by downgrading to React 18
echo "Downgrading React to version 18 for better compatibility..."

# Install React 18
npm install react@18 react-dom@18

# Install React 18 types
npm install --save-dev @types/react@18 @types/react-dom@18

echo "React downgrade complete. You can now run 'npm install' without --legacy-peer-deps" 