var title = 'Confronto fra strade in OpenStreetMap ed open data';
var mapLat = 41.8921;
var mapLon = 12.4832;
var mapZoom = 6;
var info = '<b>Strade da mappare in OpenStreetMap</b>';
info += '<p>Confronto fra strade in <a href="http://www.openstreetmap.org/" target="_blank">OSM</a> e i dati rilasciati da:';
info += '<br>- <a href="http://www.comune.verona.it/nqcontent.cfm?a_id=37426" target="_blank">Comune di Verona</a>  <a href="http://www.dati.gov.it/iodl/2.0/" target="_blank">IODL 2.0</a>';
info += '<br>- <a href="http://idt.regione.veneto.it/app/metacatalog/" target="_blank">Regione Veneto (Belluno)</a> <a href="http://www.dati.gov.it/iodl/2.0/" target="_blank">IODL 2.0</a>';
info += '<br>- <a href="http://www.comune.rimini.it/filo_diretto/open_data/-toponomastica/" target="_blank">Comune di Rimini</a> <a href="http://creativecommons.org/publicdomain/zero/1.0/" target="_blank">CC0</a>';
info += '<br><br>Dati OSM: ';
for (i in tasks) {
    info += '<br><i>- ' + tasks[i].name + ' ' + tasks[i]["analysis_time"] + '</i>';
}
info += '<br><br>Clicca sulla mappa per modificare in JOSM.';
info += '<br><br>Pagina creata tramite: <a href="https://github.com/simone-f/compare-to-osm" target="_blank">compare-to-osm</a>.';
