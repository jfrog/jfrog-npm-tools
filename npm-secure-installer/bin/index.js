#!/usr/bin/env node
const dryRun = false;

const { exec } = require("child_process");

var argv = require('yargs/yargs')(process.argv.slice(2))
    .demandCommand(1)
    .argv;
const packageName = argv['_'][0];
// console.log(packageName);

exec("npm pack --dry-run --json " + packageName, (error, stdout, stderr) => {
    if (error) {
        console.log(`ERROR: ${error.message}`);
        return 1;
    }
    if (stderr) {
        console.log(`ERROR:  ${stderr}`);
        return 1;
    }

    // console.log(stdout)
    const result = JSON.parse(stdout)
    const files = result[0]["files"]
    var shrinkwrapFound = false

    files.forEach(file => {
        // console.log(file)
        if (file["path"] === "npm-shrinkwrap.json"){
            shrinkwrapFound = true
        }
    })

    if (shrinkwrapFound){
        console.log("npm-shrinkwrap.json found on package. Package is secure.")

        if (!dryRun){
            console.log("Issuing install of package...")
            exec("npm install -g " + packageName, (error, stdout, stderr) => {
                if (error) {
                    console.log(`ERROR: ${error.message}`);
                    return 1;
                }
                if (stderr) {
                    console.log(`ERROR:  ${stderr}`);
                    return 1;
                }

                console.log(stdout)
                return 0;
            });
        }
    } else {
        console.log("ERROR: npm-shrinkwrap.json was not found on package. Will assume this package is not secure");
        return 1;
    }

});
