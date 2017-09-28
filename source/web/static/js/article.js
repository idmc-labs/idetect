$(document).ready(function(){

	function validateCoords(coords) {
		var lat = coords[0];
		var long = coords[1];
		if (lat >= -90 && lat <= 90 && long >= -180 && long <= 180) {
			return true;
		}
		else {
			return false;
		}
	}

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
	var cleanCoords = new Array();
	for (var i = 0; i < coords.length; i++) {
		if (validateCoords(coords[i])){
			markers[i] = L.marker(coords[i]).addTo(mymap);
			cleanCoords[i] = coords[i];
		}
	}

	mymap.fitBounds(cleanCoords, {maxZoom: 5});

});