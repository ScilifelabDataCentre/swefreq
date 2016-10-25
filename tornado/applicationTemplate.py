indexHead="""
<!DOCTYPE html>
<!-- define angular app -->
<html ng-app="App">
  <head>
    <!-- SCROLLS -->
    <meta charset="utf-8" />
    <!-- Bootstrap -->
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/bootstrap/3.3.2/css/bootstrap.min.css" />
    <link rel="stylesheet" href="//netdna.bootstrapcdn.com/font-awesome/4.3.0/css/font-awesome.css" />
    <script src="https://ajax.googleapis.com/ajax/libs/jquery/1.11.1/jquery.min.js"></script>
    <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.3.2/js/bootstrap.min.js"></script>
    <!-- Angular -->
    <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.0/angular.min.js"></script>
    <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.0/angular-route.min.js"></script>
    <script src="https://ajax.googleapis.com/ajax/libs/angularjs/1.5.0/angular-cookies.min.js"></script>
    <!-- Angular grid gui -->
    <link rel="stylesheet" href="/javascript/main.css" type="text/css" />
    <link rel="stylesheet" href="/javascript/local.css" type="text/css" />
    <!-- The application -->
    <script src="javascript/app.js"></script>

    <!-- Google Analytics -->
    <script>
    (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
        (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
        m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
    })(window,document,'script','https://www.google-analytics.com/analytics.js','ga');
    ga('create', 'UA-85976442-1', 'auto');
    ga('send', 'pageview');
    </script>
    <!-- End Google Analytics -->
  </head>
"""
indexHtml="""
  <!-- define angular controller -->
  <body ng-controller="mainController as mainCtrl">
    <consent></consent>
    <nav class="navbar navbar-default">
      <div class="container">
        <a class="navbar-brand" href="/#/">SweFreq</a>
        <div class="navbar-right">
          <a href="/#/about/" role="button" class="btn btn-default navbar-btn">About</a>
          <a href="/#/terms/" role="button" class="btn btn-default">Terms of use</a>
          <a href="/#/dataBeacon/" role="button" class="btn btn-default navbar-btn">Data Beacon</a>
          <a href="{{ExAC}}" role="button" class="btn btn-default navbar-btn">ExAC Browser</a>
          <a href="/#/downloadData/" role="button" class="btn btn-default navbar-btn">Download Data</a>
        {%if is_admin %}
          <a href="/#/admin/" role="button" class="btn btn-default navbar-btn">Admin</a>
        {% end %}
        {%if user_name != None%}
          {{user_name}}
          <a href="/logout" class="btn btn-text navbar-btn">Logout</a>
          {{email}}
        {% else %}
          <a href="/login" class="btn btn-text navbar-btn">Login</a>
        {% end %}
        </div>
      </div>
    </nav>
    <div id="main">
      <!-- angular templating -->
      <!-- this is where content will be injected by angular -->
      <div ng-view=""></div>
    </div>
      </div>
    <footer class="text-center"></footer>
  </body>
</html>
"""
notAuthorizedHtml="""
  <!-- define angular controller -->
  <body ng-controller="mainController as mainCtrl">
    <consent></consent>
    <nav class="navbar navbar-default">
      <div class="container">
        <a class="navbar-brand" href="/#/">SweFreq</a>
        <div class="navbar-right">
          <a href="/#/about/" role="button" class="btn btn-default navbar-btn">About</a>
          <a href="/#/terms/" role="button" class="btn btn-default">Terms of use</a>
          <a href="/#/dataBeacon/" role="button" class="btn btn-default navbar-btn">Data Beacon</a>
          <a href="{{ExAC}}" role="button" class="btn btn-default navbar-btn">ExAC Browser</a>
          <a href="/login" class="btn btn-text navbar-btn">Login</a>
        </div>
      </div>
    </nav>
    <div id="main">
      <!-- angular templating -->
      <!-- this is where content will be injected -->
      <div ng-view=""></div>
    </div>
    <footer class="text-center"></footer>
  </body>
</html>
"""
indexNoAccess="""
  <!-- define angular controller -->
  <body ng-controller="mainController as mainCtrl">
    <consent></consent>
    <nav class="navbar navbar-default">
      <div class="container">
        <a class="navbar-brand" href="/#/">SweFreq</a>
        <div class="navbar-right">
          <a href="/#/about/" role="button" class="btn btn-default navbar-btn">About</a>
          <a href="/#/terms/" role="button" class="btn btn-default">Terms of use</a>
          <a href="/#/requestAccess/" role="button" class="btn btn-default navbar-btn">Request Access</a>
        {%if user_name != None%}
          {{user_name}}
          <a href="/logout" class="btn-text navbar-btn">Logout</a>
          {{email}}
        {% else %}
          <a href="/login" class="btn-text navbar-btn">Login</a>
        {% end %}
        </div>
      </div>
    </nav>
    <div id="main">
      <!-- angular templating -->
      <!-- this is where content will be injected by angular -->
      <div ng-view=""></div>
    </div>
    <footer class="text-center"></footer>
  </body>
</html>
"""
