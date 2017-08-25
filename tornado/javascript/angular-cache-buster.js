/*
 * The MIT License (MIT)
 *
 * Copyright (c) 2014 Martin Saint-Macary
 *
 * Permission is hereby granted, free of charge, to any person obtaining a
 * copy of this software and associated documentation files (the "Software"),
 * to deal in the Software without restriction, including without limitation
 * the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the
 * Software is furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
 * FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
 * DEALINGS IN THE SOFTWARE.
 */
angular.module('ngCacheBuster', [])
  .config(['$httpProvider', function($httpProvider) {
    return $httpProvider.interceptors.push('httpRequestInterceptorCacheBuster');
  }])
    .provider('httpRequestInterceptorCacheBuster', function() {

       this.matchlist = [/.*partials.*/, /.*views.*/ ];
       this.logRequests = false;

       //Default to whitelist (i.e. block all except matches)
       this.black=false;

       //Select blacklist or whitelist, default to whitelist
       this.setMatchlist = function(list,black) {
           this.black = typeof black != 'undefined' ? black : false
           this.matchlist = list;
       };


       this.setLogRequests = function(logRequests) {
           this.logRequests = logRequests;
       };

       this.$get = ['$q', '$log', function($q, $log) {
           var matchlist = this.matchlist;
           var logRequests = this.logRequests;
           var black = this.black;
        if (logRequests) {
            $log.log("Blacklist? ",black);
        }
           return {
               'request': function(config) {
                   //Blacklist by default, match with whitelist
                   var busted= !black;

                   for(var i=0; i< matchlist.length; i++){
                       if(config.url.match(matchlist[i])) {
                           busted=black; break;
                       }
                   }

                   //Bust if the URL was on blacklist or not on whitelist
                   if (busted) {
                       var d = new Date();
                       config.url = config.url.replace(/[?|&]cacheBuster=\d+/,'');
                       //Some url's allready have '?' attached
                       config.url+=config.url.indexOf('?') === -1 ? '?' : '&'
                       config.url += 'cacheBuster=' + d.getTime();
                   }

                   if (logRequests) {
                       var log='request.url =' + config.url
                       busted ? $log.warn(log) : $log.info(log)
                   }

                   return config || $q.when(config);
               }
           }
       }];
    });
