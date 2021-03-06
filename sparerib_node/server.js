var cluster = require('cluster');

if (cluster.isMaster) {
    var cpuCount = require('os').cpus().length;

    // Create a worker for each CPU
    for (var i = 0; i < cpuCount; i += 1) {
        cluster.fork();
    }

    cluster.on('exit', function (worker) {
        console.log('Worker ' + worker.id + ' died :(');
        cluster.fork();
    });

} else {

    var express = require('express');
    var app = express();
    var Browser = require("zombie");
    var http = require('http'), httpProxy = require('http-proxy');
    var fs = require('fs'), _ = require("underscore");

    var globalBrowser = new Browser();
    var proxy = new httpProxy.RoutingProxy();

    var settingsFile = fs.readFileSync("./settings.json");
    var settings = JSON.parse(settingsFile);

    if (fs.existsSync("./local_settings.json")) {
        var localSettingsFile = fs.readFileSync("./local_settings.json");
        _.extend(settings, JSON.parse(localSettingsFile));
        console.log(settings);
    }

    globalBrowser.visit("http://" + settings.proxyHost + ":" + settings.proxyPort, function() {
        start();
    })

    app.all(/\/(api|static)\/.*/, function(req, res) {
        proxy.proxyRequest(req, res, {
            host: settings.proxyHost,
            port: settings.proxyPort
        });
    });

    app.all('*', function(req, res) {
        var browser = globalBrowser.fork();
        browser.wait(function() {
            browser.window.SIMPLE_JS = true;
            browser.window.Backbone.history.navigate(req.path, true);
            browser.wait(function() {
                browser.window.$('script[data-remove!=false]').remove();
                res.send(browser.html());
            })
        })
    });

    var start = function() {
        console.log('ready');
        app.listen(settings.port);
    }
}