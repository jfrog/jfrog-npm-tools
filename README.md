# jfrog-npm-tools

A collection of tools to help audit your NPM dependencies for suspicious packages or 
continuously monitor dependencies for future security events.

The tools:

1. [npm-secure-install](npm-secure-installer/README.md) - Validate dependencies are locked down
   to the exact versions before installation of global tools
2. [package-checker](package_checker/README.md) - Python command line tool that checks a
   dependency string for what will actually be installed and whether it is suspicious
3. [npm_issues_statistics](npm_issues_statistics/README.md) - Analyzes github comments to find
   unusual activity that might correlate to compromised dependency
