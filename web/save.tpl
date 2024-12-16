% include('head.tpl')
% from datetime import datetime, timezone
<h1>{{gs.map_name_localized}}</h1>
<div class="main" style="align-items:start">
	<div class="item" style="border:none">
		<div style="display:flex;align-items:flex-start;">
			<img src="/saveimg/{{id}}?s=2">
		</div>
		<div style="display:flex;align-items:end;">
		</div>
	</div>
	<div class="item">
		<div style="display:flex;align-items:flex-start;">
			<span class="item-header">
				{{datetime.fromtimestamp(gs.file_time, timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}}
				<br/>
				{{gs.name}}
				<br/>
				<br/>
				Здоровье {{f'{gs.health * 100:.0f}'}}%
			</span>
		</div>
		<div style="display:flex;align-items:end;">
		</div>
	</div>
</div>

%prev_section_class = None
%for ao in iter_actor_objects(gs):
	%if ao.section:
		%if (_class := ao.section.get('class', '').partition('_')[0]) and _class != prev_section_class:
			%if not prev_section_class is None:
				</div></div>
			%end
			<div style="display:grid;grid-template-rows:repeat(auto-fill,minmax(100px, auto));"><div class="item" style="grid-template-columns:repeat(auto-fill,minmax(200px, auto));align-items:normal;">
			%prev_section_class = _class
		%end
		<div class="subitem">
			<div style="display:flex;align-items:flex-start;">
				{{ao.quantity if ao.quantity != 1 else ''}} <img src="/itemimg/{{ao.section.name}}">
			</div>
			<div style="display:flex;align-items:end;">
				{{ao.localize()}}
			</div>
		</div>
	%end
%end
</div></div>

<div>
<img src="/mapimg/{{id}}">
</div>
% include('footer.tpl')
