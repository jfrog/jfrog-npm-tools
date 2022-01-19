# Package Checker

Package checker is a script that checks a node package with a given version. The program reports
several suspicious heuristics to help determine version and range (^/~) to best use in your
package.json file.
Reported heuristics:
1. Newest version is more than 10 versions ahead of the base version.
2. Newest version in range is too new - released in the past 14 days.
3. The version was released after more than a year the package was dormant.

All of these can signal a need to review the version and range and either update or pin versions
better.

## Installation

Coming to pip soon :)

## Usage

```
$ python3 package_checker.py scan-single-package rtl-detect 1.0.3
[Warning - rtl-detect] Package was recently updated (to 1.0.3) after a long time (1238 days, 14:08:13.202000. This might be a bad sign.

$ python3 package_checker.py scan-single-package @babel/core ^7.13.8
[Warning - @babel/core] There are 17 versions between the pinned version and actual version that will be installed. That might be too much
[Warning - @babel/core] Newest package 7.16.7 age is 13 days, 9:11:22.647355. It might be too new.
```

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
