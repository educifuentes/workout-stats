#!/bin/bash
set -e

# Generate today's date in calver format YY.MM.DD
VERSION="v$(date +%y.%m.%d)"

echo "Creating tag $VERSION..."
git tag $VERSION

echo "Pushing tag $VERSION to origin..."
git push origin $VERSION

echo "Release $VERSION initiated successfully!"
