% include('head.tpl')
% from datetime import datetime, timezone
<div style="text-align:center">
<h2>Сохранения</h2>
</div>
<table style="margin:auto">
% for gs in savings:
<tr>
	<td style="padding:1px 0px 7px 5px"><a href="/save/{{gs.name}}"><img src="/saveimg/{{gs.name}}"></img></a></td>
	<td style="border-top:1px solid;padding-left:5px">
		<a href="/save/{{gs.name}}"><h3>·{{gs.name}}</h3></a>
		<br/>
		<h3>{{gs.map_name_localized}}</h3>
		<br/>Здоровье {{f'{gs.health * 100:.0f}'}}%
		<br/>{{datetime.fromtimestamp(gs.file_time, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}}
	</td>
	<td style="text-align:center"><a href="/save/{{gs.name}}"><img src="/mapimg/{{gs.name}}?s=0.2"></img></a></td>
</tr>
% end
</table>
% include('footer.tpl')
