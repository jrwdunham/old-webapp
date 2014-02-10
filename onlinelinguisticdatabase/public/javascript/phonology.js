OLD.phonology = {};      // namespace of the phonology page
OLD.phonology.phonologies = {};     // holds phonology objects
OLD.phonology.menuItems = {};       // holds menu items


YAHOO.util.Event.onDOMReady(
    function () {
        // Globals
        OLD.phonology.mainContent = document.getElementById('mainContentDiv');
        OLD.phonology.phonologyHeading = document.getElementById(
                                                            'phonologyHeading');
        OLD.writeToPromptDiv('hel');
        // Main menu
        var phonMenuItems = [
            OLD.phonology.menuItems.about,
            OLD.phonology.menuItems.open,
            OLD.phonology.menuItems.new,
            OLD.phonology.menuItems.edit,
            OLD.phonology.menuItems.test,
            OLD.phonology.menuItems.delete,
            OLD.phonology.menuItems.help
        ];
        OLD.phonology.mainMenu = new YAHOO.widget.MenuBar("phonMenu", {
            autosubmenudisplay: true}
        );
        OLD.phonology.mainMenu.addItems(phonMenuItems);
        OLD.phonology.mainMenu.render('phonologymenubar');

        OLD.phonology.checkIfDependenciesAreInstalled();

        // The About Page is the default page
        OLD.phonology.getAboutPhonologies();
    }
);


// Add some default listeners to Edit, Delete and Test
YAHOO.util.Event.onAvailable('editMenuOption', function () {
    YAHOO.util.Event.addListener('editMenuOption', "click",
                                 OLD.phonology.getEditPhonologyInterface);
});
YAHOO.util.Event.onAvailable('deleteMenuOption', function () {
    YAHOO.util.Event.addListener('deleteMenuOption', "click",
                                 OLD.phonology.deletePhonology);
});
YAHOO.util.Event.onAvailable('testItselfMenuOption', function () {
    YAHOO.util.Event.addListener('testItselfMenuOption', "click",
                                 OLD.phonology.phonologizeSelf);
});
YAHOO.util.Event.onAvailable('testTokenMenuOption', function () {
    YAHOO.util.Event.addListener('testTokenMenuOption', "click",
                                 OLD.phonology.getTestPhonologyByTokenInterface);
});
YAHOO.util.Event.onAvailable('testDBMenuOption', function () {
    YAHOO.util.Event.addListener('testDBMenuOption', "click",
                                 OLD.phonology.getTestPhonologyOnDBInterface);
});


OLD.phonology.checkIfDependenciesAreInstalled = function () {
    // If foma and flookup are not installed, warn user and truncate interface

    var responseSuccess = function (o) {
        var dependenciesInstalled = YAHOO.lang.JSON.parse(o.responseText);
        if (!dependenciesInstalled) {

            // Remove Open, New, Edit, Test, Delete from main menu.
            OLD.phonology.mainMenu.clearContent();
            var phonMenuItems = [OLD.phonology.menuItems.about,
                                 OLD.phonology.menuItems.help];
            OLD.phonology.mainMenu.addItems(phonMenuItems);
            OLD.phonology.mainMenu.render();

            // Inform user that (and how) foma needs to be installed
            var msg = "<p>Sorry, the server hosting this application does " +
                        "not have foma and flookup installed.  These programs " +
                        "must be installed in order to configure and use " +
                        "an OLD phonology.  Please contact your system " +
                        "administrator.</p>";
            OLD.writeToPromptDiv(msg);
            var installFomaInstructions = document.getElementById(
                                    'installFomaInstructionsDiv').innerHTML;
            OLD.writeToHelpDiv(installFomaInstructions);
        }
    };

    var responseFailure = function (o) {return;};

    var callback = {success: responseSuccess, failure: responseFailure};

    var sUrl = '/analysis/phonology_dependencies_installed';
    var transaction = YAHOO.util.Connect.asyncRequest('GET', sUrl, callback,
                                                      null);
}
OLD.phonology.getAboutPhonologies = function () {
    // Display static HTML describing OLD phonologies
    OLD.hidePromptDiv();
    var aboutPhonologiesDiv = document.getElementById('aboutPhonologiesDiv');
    OLD.phonology.mainContent.innerHTML = aboutPhonologiesDiv.innerHTML;
}

OLD.phonology.getAddEditPhonologyFields = function () {
    // Return the HTML inputs used to add/edit a phonology
    var nameLabel = "<label for='phon_name'>Name*</label>";
    var nameErr = "<span id='phon_name_err' class='error-message'></span>";
    var nameInput = '<input type="text" id="phon_name" name="phon_name" ' +
                        'maxlength="255" style="width: 100%;" />';

    var descrLabel = '<label for="phon_description">Description</label>';
    var descrErr = '<span id="phon_description_err" class="error-message">' +
                        '</span>';
    var descrInput = '<textarea id="phon_description" ' +
                    'name="phon_description" style="width: 100%;"></textarea>';

    var scriptLabel = '<label for="phon_fomaScript">Foma Script*</label>';
    var scriptErr = '<span id="phon_fomaScript_err" class="error-message">' +
                        '</span>';
    var scriptTextArea = '<textarea id="phon_fomaScript" ' +
                        'name="phon_fomaScript" class="monospace" cols="80" ' +
                        'style="height:500px; font-size:80%;"></textarea>';

    var tags = [nameLabel, nameErr, nameInput, descrLabel, descrErr,
                descrInput, scriptLabel, scriptErr, scriptTextArea];
    return tags.join('\n');
}
OLD.phonology.getAddPhonologyInterface = function () {
    // Display the inputs to create a new phonology; "Add Phonology" button
    //  calls OLD.phonology.addPhonology()

    OLD.hidePromptDiv();

    // Write the fields to the page
    var fields = OLD.phonology.getAddEditPhonologyFields();
    var addButton = '<input type="button" name="addPhonologyButton" ' +
                        'id="addPhonologyButton" value="Add Phonology" />';
    var progInd = '<div id="progressIndicator"></div>';
    OLD.phonology.mainContent.innerHTML = [
                                        fields, addButton, progInd].join('\n');

    // Get the example foma script
    var sampleScript = [
        '# Here is an extremely simple phonology script to get you started',
        '# define wordFinalDevoicingD d -> t || _ "#";',
        '# define nasalPlaceAssimilation n -> m || _ [p|b|f];',
        '# define phonology wordFinalDevoicingD .o. nasalPlaceAssimilation;'
    ]
    sampleScript = sampleScript.join('\n');

    // Update the fields: insert example script, bind 'Add Phonology' button
    YAHOO.util.Event.onAvailable('phon_fomaScript', function () {
        var scriptTextarea = document.getElementById('phon_fomaScript');
        scriptTextarea.value = sampleScript;
    });
    YAHOO.util.Event.onAvailable('addPhonologyButton', function () {
        YAHOO.util.Event.addListener('addPhonologyButton', "click",
                                     OLD.phonology.addPhonology);
    });
}

OLD.phonology.getOpenPhonologyInterface = function () {
    // Get all phonologies; update global OLD.phonology.phonologies;
    //  display phonologies that can be opened in the promptDiv.
    function populatePromptDivWithPhonologies(phonologies) {
        if (phonologies.length > 0) {
            var msg = "Click a phonology name to open it.";
            for (var i = 0; i < phonologies.length; i++) {
                var phonology = phonologies[i];
                OLD.phonology.phonologies[phonology['id']] = phonology;
                var phonViewID = "phonology_" + phonology['id'] + "_view";
                msg += "<div><a class='openOption' id='" + phonViewID +
                    "'>" + phonology['name'] + "</a></div>\n";
                var displayer = function () {
                    OLD.phonology.displayPhonologyByID(phonology.id);
                }
                YAHOO.util.Event.onAvailable(phonViewID, function () {
                    YAHOO.util.Event.addListener(phonViewID, "click", displayer);
                });
            }
            OLD.writeToPromptDiv(msg);
        } else {
            var msg = "<p>There are no phonologies.</p>" +
                        "<p><a id='newPhonologyAnchor'>Create one.</a></p>";
            OLD.writeToPromptDiv(msg);
            YAHOO.util.Event.onAvailable('newPhonologyAnchor', function () {
                YAHOO.util.Event.addListener('newPhonologyAnchor', "click",
                                        OLD.phonology.getAddPhonologyInterface);
            });
        }
    }

    // Use OLD.phonology.phonologies while waiting for the Ajax response
    if (Object.size(OLD.phonology.phonologies) != 0) {
        var temp = [];
        for (var key in OLD.phonology.phonologies) {
            temp.push(OLD.phonology.phonologies[key]);
        }
        populatePromptDivWithPhonologies(temp);
    }

    var responseSuccess = function (o) {
        var phonologies = YAHOO.lang.JSON.parse(o.responseText);
        populatePromptDivWithPhonologies(phonologies);
    };

    var responseFailure = function (o) {return;};

    var callback = {success: responseSuccess, failure: responseFailure};

    var sUrl = '/analysis/phonology_get';
    YAHOO.util.Connect.setDefaultPostHeader(false);
    YAHOO.util.Connect.initHeader("Content-Type",
                            "application/json; charset=utf-8");
    var transaction = YAHOO.util.Connect.asyncRequest(
                            'POST', sUrl, callback, null);
}

OLD.phonology.getFomaScriptOverviewDiv = function () {
    // Display the static HTML that overviews foma syntax.
    var fomaScriptOverviewDiv = document.getElementById(
                                                'fomaScriptOverviewDiv');
    OLD.phonology.mainContent.innerHTML = fomaScriptOverviewDiv.innerHTML;
}

OLD.phonology.getExampleFomaScriptDiv = function () {
    // Display the static HTML that provides an example foma script.
    var exampleFomaScriptDiv = document.getElementById('exampleFomaScriptDiv');
    OLD.phonology.mainContent.innerHTML = exampleFomaScriptDiv.innerHTML;
}
OLD.phonology.getFomaInstallationInstructions = function () {
    // Display the static HTML that explains how to install foma.
    var installFomaInstructionsDiv = document.getElementById(
                                                'installFomaInstructionsDiv');
    OLD.phonology.mainContent.innerHTML = installFomaInstructionsDiv.innerHTML;
}
OLD.phonology.getPhonologyTesterScriptDiv = function () {
    // Display the static HTML that lists the phonology tester Python script.
    var phonologyTesterScriptDiv = document.getElementById(
                                            'phonologyTesterScriptDiv');
    OLD.phonology.mainContent.innerHTML = phonologyTesterScriptDiv.innerHTML;
}

OLD.phonology.inPageHelp = function () {
    // Display the foma scripting overview HTML in the help div.
    var fomaScriptOverviewDiv = document.getElementById(
                                                    'fomaScriptOverviewDiv');
    OLD.writeToHelpDiv(fomaScriptOverviewDiv.innerHTML);
}

OLD.phonology.inPageInstructions = function () {
    // Display the static HTML script-writing instructions in the help div.
    var fomaPhonologyScriptInstructionsDiv = document.getElementById(
                                    'fomaPhonologyScriptInstructionsDiv');
    OLD.writeToHelpDiv(fomaPhonologyScriptInstructionsDiv.innerHTML);
}

OLD.phonology.getEditPhonologyInterface = function (ID) {
    // Display the inputs to edit a phonology; "Edit Phonology" button
    //  calls OLD.phonology.editPhonology()
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                                "before you can edit one.</p>"
        return;
    }

    // Create the fields
    var fields = OLD.phonology.getAddEditPhonologyFields();
    var idInput = '<input type="hidden" id="phon_id" value="' + ID + '"/>';
    var editButton = '<input type="button" name="editPhonologyButton" ' + 
                        'id="editPhonologyButton" value="Edit Phonology" />';
    var progInd = '<div id="progressIndicator"></div>';
    var components = [fields, idInput, editButton, progInd];
    OLD.phonology.mainContent.innerHTML = components.join('\n');

    // Put the phonology's values into the fields and bind editPhonology
    YAHOO.util.Event.onAvailable('phon_name', function () {
        var nameInput = document.getElementById('phon_name');
        nameInput.value = phonology.name;
    });
    YAHOO.util.Event.onAvailable('phon_description', function () {
        var descriptionTextarea = document.getElementById('phon_description');
        descriptionTextarea.value = phonology.description;
    });
    YAHOO.util.Event.onAvailable('phon_fomaScript', function () {
        var scriptTextarea = document.getElementById('phon_fomaScript');
        scriptTextarea.value= phonology.script;
    });
    YAHOO.util.Event.onAvailable('editPhonologyButton', function () {
        YAHOO.util.Event.addListener('editPhonologyButton', "click",
                                     OLD.phonology.editPhonology);
    });
}
OLD.phonology.getTestPhonologyByTokenInterface = function (ID) {
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                                "before you can test one.</p>"
        return;
    }
    var testPhonologyByTokenDiv = document.getElementById(
                                        'testPhonologyByTokenDiv');
    var testPhonologyByTokenInstructions = document.getElementById(
                            'testPhonologyByTokenInstructionsDiv').innerHTML;
    OLD.phonology.mainContent.innerHTML = testPhonologyByTokenDiv.innerHTML;
    OLD.writeToHelpDiv(testPhonologyByTokenInstructions);

    var phonologizer = function () {
        OLD.phonology.phonologizeToken(ID);
    }
    YAHOO.util.Event.onAvailable('phonologizeButton', function () {
        YAHOO.util.Event.addListener('phonologizeButton', "click",
                                     phonologizer);
    });
}
OLD.phonology.phonologizeToken = function (ID) {
    var token = document.getElementById('token').value;
    var responseDiv = document.getElementById('phonologizeByTokenResponseDiv');

    var responseSuccess = function (o) {
        var surfaceForms = YAHOO.lang.JSON.parse(o.responseText);
        responseDiv.innerHTML = "<p>" + surfaceForms.join("</p><p>") + "</p>";
    };

    var responseFailure = function (o) {return;};

    var callback = {success: responseSuccess, failure: responseFailure};

    var input = {token: token, id: ID};
    input = YAHOO.lang.JSON.stringify(input);
    var sUrl = '/analysis/phonology_apply_to_token';
    YAHOO.util.Connect.setDefaultPostHeader(false);
    YAHOO.util.Connect.initHeader("Content-Type",
                                  "application/json; charset=utf-8");
    var transaction = YAHOO.util.Connect.asyncRequest('POST', sUrl, callback,
                                                      input);
}
OLD.phonology.getTestPhonologyOnDBInterface = function (ID) {
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                "before you can test one against the DB.</p>";
        return;
    }
    OLD.phonology.mainContent.innerHTML = '<p>Testing ' + phonology.name +
        ' against the database.</p>';
}
OLD.phonology.allExpectedSurfaceFormsAreInResult = function (expecteds, result) {
    for (var i = 0; i < expecteds.length; i ++) {
        var expected = expecteds[i];
        if (result.indexOf(expected) == -1) {
            return false;
        }
    }
    return true;
}
OLD.phonology.phonologizeSelf = function (ID) {
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                "before you can test one against itself.</p>";
        return;
    }

    // Write the instructions to the help div
    var instructions = document.getElementById(
                                'testPhonologyOnSelfInstructionsDiv').innerHTML
    OLD.writeToHelpDiv(instructions);

    // Write the empty DIV elements to main content
    var statsDiv = "<div id='testStats'><progress value='50%' max='200'>50%" +
                    "</progress></div>";
    var failureDiv = "<div id='testFailure' class='warning-message'></div>";
    var successDiv = "<div id='testSuccess'></div>";
    OLD.phonology.mainContent.innerHTML = [
                                statsDiv, failureDiv, successDiv].join('\n');

    statsDiv = document.getElementById('testStats');
    failureDiv = document.getElementById('testFailure');
    successDiv = document.getElementById('testSuccess');

    var responseSuccess = function (o) {
        var tests = YAHOO.lang.JSON.parse(o.responseText);
        var successes = 0;
        for (var i = 0; i < tests.length; i ++) {
            var test = tests[i];
            var input = test[0];
            var expecteds = test[1];
            var result = test[2];
            var success = OLD.phonology.allExpectedSurfaceFormsAreInResult(
                                                            expecteds, result);
            if (success) {
                var msg = "<p>Success on " + input + ":</p><ul><li>expected: " +
                        expecteds.join(', ') + "</li><li>result: " +
                        result.join(', ') + "</li></ul>";
                successDiv.innerHTML += msg;
                successes += 1;
            } else {
                var msg = "<p>Failure on " + input + ":</p><ul><li>expected: " +
                        expecteds.join(', ') + "</li><li>result: " +
                        result.join(', ') + "</li></ul>";
                failureDiv.innerHTML += msg;
            }
        }
        var accuracy = ((successes / tests.length) * 100).toFixed(2);
        statsDiv.innerHTML = "<p>" + accuracy + "% accuracy (" + tests.length +
                            " tests, " + successes + " correct)</p>";
    };
    var responseFailure = function (o) {return;};

    var input = YAHOO.lang.JSON.stringify({id: ID});
    var callback = {success: responseSuccess, failure: responseFailure};
    var sUrl = '/analysis/phonology_apply_to_self';
    var transaction = YAHOO.util.Connect.asyncRequest('POST', sUrl, callback,
                                                      input);
}
OLD.phonology.displayPhonology = function (phonologyObject) {

    // Metadata into help div
    var metadata = "<ul>";
    if (phonologyObject['description']) {
        metadata += "<li>Description: " + phonologyObject.description + "</li>";
    }
    metadata += "<li>ID: " + phonologyObject.id + "</li>";
    metadata += "<li>Entered by " + phonologyObject.enterer + "</li>";
    metadata += "<li>Entered at " + phonologyObject.datetimeEntered + "</li>";
    if (phonologyObject.modifier) {
        metadata += "<li>Modified by " + phonologyObject.modifier + "</li>";
    }
    metadata += "<li>Last modification at " +
                phonologyObject.datetimeModified + "</li>";
    metadata += "</ul>";
    OLD.writeToHelpDiv(metadata);

    // Name into page heading
    OLD.phonology.phonologyHeading.innerHTML = "Phonology: " +
                                                phonologyObject.name;
    var viewer = function () {
        OLD.phonology.displayPhonologyByID(phonologyObject.id);
    }
    YAHOO.util.Event.addListener('phonologyHeading', 'click', viewer);

    // Script into main content
    OLD.phonology.mainContent.innerHTML = "<br /><pre class='no-margin'>" +
                            "<code>" + phonologyObject.script + "</code></pre>";

    //alert('compiledSuccessfully: ' + phonologyObject.compiledSuccessfully);

    // Bind edit, delete, test in menubar
    OLD.phonology.bindEditDeleteTestMenuItems(phonologyObject);

    window.scrollTo(0,0);
}
OLD.phonology.bindEditDeleteTestMenuItems = function (phonology) {
    // Bind the edit, delete and test menu items to the function calls
    //  appropriate to the phonology currently "opened".
    YAHOO.util.Event.removeListener("editMenuOption", "click");
    YAHOO.util.Event.removeListener("deleteMenuOption", "click");
    YAHOO.util.Event.removeListener("testItselfMenuOption", "click");
    YAHOO.util.Event.removeListener("testTokenMenuOption", "click");
    YAHOO.util.Event.removeListener("testDBMenuOption", "click");
    var editor = function () {
        OLD.phonology.getEditPhonologyInterface(phonology.id);
    }
    var deleter = function () {
        OLD.phonology.deletePhonology(phonology.id);
    }
    var testerOnSelf = function () {
        OLD.phonology.phonologizeSelf(phonology.id);
    }
    var testerByToken = function () {
        OLD.phonology.getTestPhonologyByTokenInterface(phonology.id);
    }
    var testerOnDB = function () {
        OLD.phonology.getTestPhonologyOnDBInterface(phonology.id);
    }
    YAHOO.util.Event.addListener("editMenuOption", "click", editor);
    YAHOO.util.Event.addListener("deleteMenuOption", "click", deleter);
    YAHOO.util.Event.addListener("testItselfMenuOption", "click", testerOnSelf);
    YAHOO.util.Event.addListener("testTokenMenuOption", "click", testerByToken);
    YAHOO.util.Event.addListener("testDBMenuOption", "click", testerOnDB);
}
OLD.phonology.displayPhonologyByID = function (ID) {
    // Look up the phonology by ID in the OLD.phonology.phonologies object and
    //  display
    OLD.hidePromptDiv();
    var phonology = OLD.phonology.phonologies[ID];
    OLD.phonology.displayPhonology(phonology);
}

OLD.phonology.validateAddPhonologyInputs = function (inputs) {
    // Validate the inputs: provide feedback to user via DOM and return false
    //  if not valid.
    var phon_name_err = document.getElementById('phon_name_err');
    var phon_fomaScript_err = document.getElementById('phon_fomaScript_err');
    var valid = true;
    if (inputs['name'] == "") {
        phon_name_err.innerHTML = "required field";
        valid = false;
    }
    if (inputs['script'] == "") {
        phon_fomaScript_err.innerHTML = "required field";
        valid = false;
    }
    if (inputs['script'].search(/(\n|\r|\r\n)define phonology/) == -1) {
        phon_fomaScript_err.innerHTML = 
                                "script must define an FST named phonology";
        valid = false;
    }
    return valid;
}

OLD.phonology.addPhonology = function () {
    // If inputs are valid, send Ajax POST call to add phonology, i.e., add to
    //  db and write files.

    // First disable the Edit button to prevent double calls
    var addPhonologyButton = document.getElementById('addPhonologyButton');
    addPhonologyButton.disabled = true;

    var phon_name = document.getElementById('phon_name');
    var phon_description = document.getElementById('phon_description');
    var phon_fomaScript = document.getElementById('phon_fomaScript');
    var progressIndicator = document.getElementById('progressIndicator');

    progressIndicator.innerHTML = "<progress value='50%' max='200'>50%" +
                                    "</progress>";

    var addPhonologyInputs = {
        name: phon_name.value,
        description: phon_description.value,
        script: phon_fomaScript.value
    };
    var inputsAreValid = OLD.phonology.validateAddPhonologyInputs(
                                                            addPhonologyInputs);

    var responseSuccess = function (o) {
        var phonologyObject = YAHOO.lang.JSON.parse(o.responseText);
        OLD.phonology.phonologies[phonologyObject['id']] = phonologyObject;
        OLD.phonology.displayPhonology(phonologyObject);
    };

    var responseFailure = function (o) { 
        progressIndicator.innerHTML = "Error: unable to save phonology.";
    };

    var callback = {success: responseSuccess, failure: responseFailure};

    if (inputsAreValid) {
        addPhonologyInputs = YAHOO.lang.JSON.stringify(addPhonologyInputs);
        var sUrl = '/analysis/phonology_add';
        YAHOO.util.Connect.setDefaultPostHeader(false);
        YAHOO.util.Connect.initHeader("Content-Type",
                                      "application/json; charset=utf-8");
        var transaction = YAHOO.util.Connect.asyncRequest(
                                'POST', sUrl, callback, addPhonologyInputs);
    } else {
        progressIndicator.innerHTML = "";
        addPhonologyButton.disabled = false;
        window.scrollTo(0,0);
    }
}

OLD.phonology.editPhonology = function () {
    // If inputs are valid, send Ajax POST call to edit phonology, i.e, update
    //  db and write files if necessary.

    // First disable the Edit button to prevent double calls
    var editPhonologyButton = document.getElementById('editPhonologyButton');
    editPhonologyButton.disabled = true;

    var phon_id = document.getElementById('phon_id');
    var phon_name = document.getElementById('phon_name');
    var phon_description = document.getElementById('phon_description');
    var phon_fomaScript = document.getElementById('phon_fomaScript');
    var progressIndicator = document.getElementById('progressIndicator');

    progressIndicator.innerHTML = "<progress value='50%' max='200'>50%" +
                                    "</progress>";

    var editPhonologyInputs = {
        id: phon_id.value,
        name: phon_name.value,
        description: phon_description.value,
        script: phon_fomaScript.value
    };
    var inputsAreValid = OLD.phonology.validateAddPhonologyInputs(
                                                        editPhonologyInputs);

    var responseSuccess = function (o) {
        var phonologyObject = YAHOO.lang.JSON.parse(o.responseText);
        OLD.phonology.phonologies[phonologyObject['id']] = phonologyObject;
        OLD.phonology.displayPhonology(phonologyObject);
    };

    var responseFailure = function (o) { 
        progressIndicator.innerHTML = "Error: unable to update phonology.";
    };

    var callback = {success: responseSuccess, failure: responseFailure};

    if (inputsAreValid) {
        editPhonologyInputs = YAHOO.lang.JSON.stringify(editPhonologyInputs);
        var sUrl = '/analysis/phonology_edit';
        YAHOO.util.Connect.setDefaultPostHeader(false);
        YAHOO.util.Connect.initHeader("Content-Type",
                                      "application/json; charset=utf-8");
        var transaction = YAHOO.util.Connect.asyncRequest(
                                'POST', sUrl, callback, editPhonologyInputs);
    } else {
        progressIndicator.innerHTML = "";
        editPhonologyButton.disabled = true;
        window.scrollTo(0,0);
    }
}
OLD.phonology.deletePhonology = function (ID) {
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                            "before you can delete one.</p>";
        return;
    }

    var name = phonology.name;
    var confirm = "<p>Do you really want to delete " + name + "?</p>" +
                "<p><input type='button' id='doNotDelete' value='No' /></p>" +
                "<p><input type='button' id='confirmDelete' value='Yes' /></p>";
    OLD.writeToPromptDiv(confirm);

    // The "No" button closes the prompt
    YAHOO.util.Event.onAvailable('doNotDelete', function () {
        YAHOO.util.Event.addListener('doNotDelete', "click", OLD.hidePromptDiv);
    });

    // The "Yes" button binds to reallyDeletePhonology
    YAHOO.util.Event.onAvailable('confirmDelete', function () {
        var reallyDelete = function () {
            OLD.hidePromptDiv();
            OLD.phonology.reallyDeletePhonology(ID);
        }
        YAHOO.util.Event.addListener('confirmDelete', "click", reallyDelete);
    });
}
OLD.phonology.reallyDeletePhonology = function (ID) {
    var deleter = function () {OLD.phonology.deletePhonology(ID);}
    var phonology = OLD.phonology.phonologies[ID];
    if (typeof phonology == "undefined") {
        OLD.phonology.mainContent.innerHTML = "<p>You must open a phonology " +
                                            "before you can delete one.</p>";
        return;
    }
    var name = phonology.name;

    // First disable the Delete button to prevent double calls
    YAHOO.util.Event.removeListener('deleteMenuOption', "click")

    OLD.phonology.mainContent.innerHTML = "<p><progress value='50%' " +
                                            "max='200'>50%</progress></p>";

    var responseSuccess = function (o) {
        var phonologyDeleted = YAHOO.lang.JSON.parse(o.responseText);
        if (phonologyDeleted) {
            delete OLD.phonology.phonologies[ID];
            OLD.phonology.mainContent.innerHTML = "<p>" + name +
                                                    " has been deleted.</p>";
            YAHOO.util.Event.addListener('deleteMenuOption', "click",
                                         OLD.phonology.deletePhonology);
        } else {
            OLD.phonology.mainContent.innerHTML = "<p>Server Error: unable " +
                                                "to delete " + name + ".</p>";
            YAHOO.util.Event.addListener("deleteMenuOption", "click", deleter);
        }
    };

    var responseFailure = function (o) { 
        OLD.phonology.mainContent.innerHTML = "<p>Ajax Error: unable to " +
                                                "delete " + name + ".</p>";
        YAHOO.util.Event.addListener("deleteMenuOption", "click", deleter);
    };

    var callback = {success: responseSuccess, failure: responseFailure};

    var sUrl = '/analysis/phonology_delete';
    idToDelete = YAHOO.lang.JSON.stringify(ID);
    YAHOO.util.Connect.setDefaultPostHeader(false);
    YAHOO.util.Connect.initHeader("Content-Type",
                                  "application/json; charset=utf-8");
    var transaction = YAHOO.util.Connect.asyncRequest(
                            'POST', sUrl, callback, idToDelete);
}
OLD.phonology.applyPhonologyToDB = function () {
    var responseDiv = document.getElementById(
                                        'applyPhonologyToDBResponseDiv');
    var formSearchValues = OLD.getFormSearchValues();
    var formSearchValuesJSON = YAHOO.lang.JSON.stringify(formSearchValues);

    var responseSuccess = function (o) {
        return;
    };

    var responseFailure = function (o) {
        return;
    };

    var callback = {success: responseSuccess, failure: responseFailure};

    var sUrl = '/analysis/phonology_apply_to_db';
    var transaction = YAHOO.util.Connect.asyncRequest('POST', sUrl, callback,
                                                      formSearchValuesJSON);
}


// menu items; accessible so the menu can be changed on the fly
OLD.phonology.menuItems.about = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.about.text = "About";
OLD.phonology.menuItems.about.onclick = {fn: OLD.phonology.getAboutPhonologies};
OLD.phonology.menuItems.open = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.open.text = "Open";
OLD.phonology.menuItems.open.onclick = {
    fn: OLD.phonology.getOpenPhonologyInterface};
//OLD.phonology.menuItems.open.onclick = {fn: zzz};
OLD.phonology.menuItems.new = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.new.text = "New";
OLD.phonology.menuItems.new.onclick = {
    fn: OLD.phonology.getAddPhonologyInterface};
OLD.phonology.menuItems.edit = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.edit.text = "Edit";
OLD.phonology.menuItems.edit.id = "editMenuOption";
OLD.phonology.menuItems.test = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.test.text = "Test";
OLD.phonology.menuItems.test.id = "testMenuOption";
OLD.phonology.menuItems.test.submenu = {
    id: "testsubmenu",
    itemdata: [
        {
            text: "Test Phonology on Token",
            id: "testTokenMenuOption"
        },
        {
            text: "Test Phonology on Itself",
            id: "testItselfMenuOption"
        },
        {
            text: "Test Phonology on Database",
            id: "testDBMenuOption"
        }
    ]
}

OLD.phonology.menuItems.delete = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.delete.text = "Delete";
OLD.phonology.menuItems.delete.id = "deleteMenuOption"
OLD.phonology.menuItems.help = new YAHOO.widget.MenuItem();
OLD.phonology.menuItems.help.text = "Help";
OLD.phonology.menuItems.help.onclick = {
    fn: OLD.phonology.getFomaScriptOverviewDiv};
OLD.phonology.menuItems.help.submenu = {
    id: "helpsubmenu",
    itemdata: [
        {
            text: "Foma Scripting Overview",
            onclick: {
                fn: OLD.phonology.getFomaScriptOverviewDiv
            }
        },
        {
            text: "Foma Scripting Overview (in-page)",
            onclick: {
                fn: OLD.phonology.inPageHelp
            }
        },
        {
            text: "Phonology-writing Instructions (in-page)",
            onclick: {
                fn: OLD.phonology.inPageInstructions
            }
        },
        {
            text: "Example Foma Script",
            onclick: {
                fn: OLD.phonology.getExampleFomaScriptDiv
            }
        },
        {
            text: "Phonology Tester Script",
            onclick: {
                fn: OLD.phonology.getPhonologyTesterScriptDiv
            }
        },
        {
            text: "How to Install foma",
            onclick: {
                fn: OLD.phonology.getFomaInstallationInstructions
            }
        }
    ]
}
