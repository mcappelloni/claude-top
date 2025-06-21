# Publishing claude-top to npm

## Prerequisites
1. Create an npm account at https://www.npmjs.com/
2. Login to npm: `npm login`

## Publishing Steps

### 1. Test the Package Locally
```bash
# Create a tarball
npm pack

# Test installation globally
npm install -g ./claude-top-0.0.1.tgz

# Test running
claude-top --help

# Test with npx
npx ./claude-top-0.0.1.tgz
```

### 2. Publish to npm
```bash
# Dry run to see what will be published
npm publish --dry-run

# Publish to npm registry
npm publish

# The package will be available at:
# https://www.npmjs.com/package/claude-top
```

### 3. Test Published Package
```bash
# Test with npx (no installation)
npx claude-top

# Test global installation
npm install -g claude-top
claude-top
```

### 4. Create GitHub Release
1. Go to https://github.com/mcappelloni/claude-top/releases/new
2. Choose tag: v0.0.1
3. Release title: "v0.0.1 - Initial Release"
4. Copy content from CHANGELOG.md
5. Attach the tarball (claude-top-0.0.1.tgz)
6. Publish release

## Future Releases

Use the release script:
```bash
./release.sh
```

Then follow steps 2-4 above.

## Troubleshooting

### If npm publish fails:
- Check npm login: `npm whoami`
- Ensure package name is available
- Check .npmignore is not excluding required files

### If npx doesn't work:
- Wait a few minutes for npm CDN to update
- Clear npx cache: `npm cache clean --force`