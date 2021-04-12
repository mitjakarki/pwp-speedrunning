"use strict";

const DEBUG = true;
const MASONJSON = "application/vnd.mason+json";
const PLAINJSON = "application/json";

function renderError(jqxhr) {
    let msg = jqxhr.responseJSON["@error"]["@message"];
    $("div.notification").html("<p class='error'>" + msg + "</p>");
}

function renderMsg(msg) {
    $("div.notification").html("<p class='msg'>" + msg + "</p>");
}

function getResource(href, renderer) {
    $.ajax({
        url: href,
        success: renderer,
        error: renderError
    });
}

function sendData(href, method, item, postProcessor) {
    $.ajax({
        url: href,
        type: method,
        data: JSON.stringify(item),
        contentType: PLAINJSON,
        processData: false,
        success: postProcessor,
        error: renderError
    });
}

function areaRow(item) {
    let link = "<a href='" +
                item["@controls"].self.href +
                "' onClick='followLink(event, this, renderArea)'>show</a>";

    return "<tr><td>" + item.name +
            "</td><td>" + link + "</td></tr>";
}

function measurementRow(item) {
    return "<tr><td>" + item.time +
                "</td><td>" + item.value +
                "</td></tr>";
}

function appendAreaRow(body) {
    $(".resulttable tbody").append(areaRow(body));
}

function getSubmittedArea(data, status, jqxhr) {
    renderMsg("Successful");
    let href = jqxhr.getResponseHeader("Location");
    if (href) {
        getResource(href, appendAreaRow);
    }
}

function followLink(event, a, renderer) {
    event.preventDefault();
    getResource($(a).attr("href"), renderer);
}

function submitArea(event) {
    event.preventDefault();

    let data = {};
    let form = $("div.form form");
    data.name = $("input[name='name']").val();
    sendData(form.attr("action"), form.attr("method"), data, getSubmittedArea);
}

function renderAreaForm(ctrl) {
    let form = $("<form>");
    let name = ctrl.schema.properties.name;
    form.attr("action", ctrl.href);
    form.attr("method", ctrl.method);
    form.submit(submitArea);
    form.append("<label>" + name.description + "</label>");
    form.append("<input type='text' name='name'>");
    ctrl.schema.required.forEach(function (property) {
        $("input[name='" + property + "']").attr("required", true);
    });
    form.append("<input type='submit' name='submit' value='Submit'>");
    $("div.form").html(form);
}

function renderArea(body) {
    $("div.navigation").html(
        "<a href='" +
        body["@controls"].collection.href +
        "' onClick='followLink(event, this, renderAreas)'>Areas</a>" 
		// tähän varmaan sitten render events in the area
		//+
		//"<a href='" +
        //body["@controls"]["nearby:areas-collection"].href +
        //"' onClick='followLink(event, this, renderEVETNSBLABLABLA)'>collection</a>"
    );
    $(".resulttable thead").empty();
    $(".resulttable tbody").empty();
    renderAreaForm(body["@controls"].edit);
    $("input[name='name']").val(body.name);
    $("form input[type='submit']").before(
        "<label>Location</label>" +
        "<input type='text' name='name' value='" +
        body.location + "' readonly>"
    );
}

function renderAreas(body) {
    $("div.navigation").empty();
    $("div.tablecontrols").empty();
    $(".resulttable thead").html(
        "<tr><th>Name</th><th>Model</th><th>Location</th><th>Actions</th></tr>"
    );
    let tbody = $(".resulttable tbody");
    tbody.empty();
    body.items.forEach(function (item) {
        tbody.append(areaRow(item));
    });
    renderAreaForm(body["@controls"]["nearby:add-area"]);
}

function renderMeasurements(body) {
	let prev_element = ""
	let next_element = ""
	$("div.navigation").empty();
	if (body["@controls"].prev) {
      prev_element = "<a href='" +
					body["@controls"].prev.href +
					"' onClick='followLink(event, this, renderMeasurements)'>prev</a>"
    }
	if (body["@controls"].next) {
      next_element = "<a href='" +
					body["@controls"].next.href +
					"' onClick='followLink(event, this, renderMeasurements)'>next</a>"
    }
	$("div.tablecontrols").html(
      prev_element + " | " + next_element
    );
	$(".resulttable thead").html(
        "<tr><th>Time</th><th>Value</th></tr>"
    );
	let tbody = $(".resulttable tbody");
    tbody.empty();
	body.items.forEach(function (item) {
        tbody.append(measurementRow(item));
    });
}

$(document).ready(function () {
    getResource("http://localhost:5000/api/areas/", renderAreas);
});