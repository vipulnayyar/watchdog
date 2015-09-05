function get_processes (duration) {
	
	$.get( "api/get_processes?duration="+duration, function( data ) {
		
		var	obj = data;
		console.log(obj);
		
		content = "<table class=\"table table-condensed table-striped table-bordered\"><thead><tr> <th> Process ID</th> <th> Received bytes </th> <th> Sent bytes </th> <th> Total Bandwidth </th>  </tr></thead><tbody>";
		for (var i = obj.length - 1; i >= 0; i--) {
	
			content += "<tr>";
			content += "<td> <a href=\"process/"+ obj[i]["pid"]+"\"> " + obj[i]["pid"]+ "</a></td>";
			
			var read = 0, write = 0;

			for (var j = obj[i]["data"].length - 1; j >= 0; j--) {
				read += obj[i]["data"][j][1];
				write += obj[i]["data"][j][2];
				
			};

			content += "<td>" + read+ "</td>";
			content += "<td>" + write+ "</td>";
			
			var bandwith = read + write;
			content += "<td>" + bandwith + "</td>";

			content += "</tr>";
		};		
		content +="</tbody></table>";	

		$("#ptable").html(content);
	});

	
}

get_processes(100);