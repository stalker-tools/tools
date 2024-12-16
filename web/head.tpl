<html>
	<head>
		<title>{{game.config.title}}</title>
		<style type ="text/css">
			.black{
				background-color: black;
				color: bisque;
			}
			.header{
				text-align: center;
			}
			.footer{
				position: fixed;     
				text-align: center;    
				bottom: 0px; 
				width: 100%;
			}
			.main { display:grid;grid-template-columns:repeat(auto-fill,375px); }
			.description { display:grid;grid-template-columns:repeat(auto-fill,670px);grid-template-rows:min-content;align-content:flex-start; }
			.item { display:grid;padding:10px;margin:7px;border:1px outset;border-radius:15px;align-items:flex-start;grid-template-rows:min-content; }
			.subitem { display:grid;padding:10px;margin:7px;grid-template-rows:min-content; }
			.item-description { display:grid;padding:10px;margin:7px; }
			.item-header { font-weight:bold;font-size:larger; }
			.stroke-bg {
				background: url("data:image/svg+xml,%3Csvg viewBox='0 0 20 300' xmlns='http://www.w3.org/2000/svg'%3E %3Cpath vector-effect='non-scaling-stroke' transform='rotate(-30)' opacity='15%' stroke='currentColor' d='M 0,0 l 0,100'/%3E %3Cpath stroke='currentColor' d='M 0,0 l 20,0'/%3E %3C/svg%3E");
			}
		</style>
	 </head>
	<body class="{{'black' if game.is_black_style else ''}}">
		<h1 class="header">{{game.config.title}}</h1>
		<hr />
