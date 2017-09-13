$(document).ready(function(){

	if (coords.length > 0){
		var mymap = L.map('mapid').setView(coords[0], 3);
	}
	else{
		var mymap = L.map('mapid').setView([0, 0], 3);
	}

	// var layer = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png', {
 //  		attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attributions">CARTO</a>'
	// }).addTo(mymap);

	var layer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}', {
				attribution: 'Tiles &copy; Esri &mdash; Source: Esri, DeLorme, NAVTEQ, USGS, Intermap, iPC, NRCAN, Esri Japan, METI, Esri China (Hong Kong), Esri (Thailand), TomTom, 2012'
			}).addTo(mymap);

	var markers = new Array();

	for (var i = 0; i < coords.length; i++) {
	    markers[i] = L.marker(coords[i]).addTo(mymap);
	}

	mymap.fitBounds(coords, {maxZoom: 5});

});