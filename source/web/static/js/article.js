$(document).ready(function(){

	var mymap = L.map('mapid').setView(coords[0], 3);

	var layer = L.tileLayer('https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png', {
  		attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors, &copy; <a href="https://carto.com/attributions">CARTO</a>'
	}).addTo(mymap);

	var markers = new Array();

	for (var i = 0; i < coords.length; i++) {
	    markers[i] = L.marker(coords[i]).addTo(mymap);
	}

});