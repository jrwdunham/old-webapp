var OLD = {};

YAHOO.util.Event.onDOMReady(function () {
    OLD.prompt = document.getElementById('promptDiv');
    OLD.promptinner = document.getElementById('promptDivInner');
    OLD.help = document.getElementById('helpDiv');
    OLD.helpinner = document.getElementById('helpDivInner');

    // Set global event listeners
    YAHOO.util.Event.addListener("closePromptDivButton", "click",
                                 OLD.hidePromptDiv);
});

OLD.showHidePromptDiv = function () {
    if (OLD.prompt.display == "none") {
        OLD.showPromptDiv();
    } else {
        OLD.hidePromptDiv();
    }
}

OLD.showPromptDiv = function () {
    OLD.prompt.style.display = "block";
    OLD.prompt.style.visibility = "visible";
}

OLD.hidePromptDiv = function () {
    OLD.prompt.style.display = "none";
    OLD.prompt.style.visibility = "hidden";
}

OLD.writeToPromptDiv = function (content) {
    OLD.showPromptDiv();
    OLD.promptinner.innerHTML = content;
}

OLD.showHelpDiv = function () {
    OLD.help.style.display = "block";
    OLD.help.style.visibility = "visible";
}

OLD.hideHelpDiv = function () {
    OLD.help.style.display = "none";
    OLD.help.style.visibility = "hidden";
}

OLD.writeToHelpDiv = function (content) {
    OLD.showHelpDiv();
    OLD.helpinner.innerHTML = content;
}


OLD.getFormSearchValues = function () {
    var searchValues = {};
    var elements = document.getElementById('formSearchTable').elements;
    for(var i = 0; i < elements.length; i++)
    {
        var element = elements[i];
        if (['INPUT', 'SELECT'].indexOf(element.tagName) != -1) {
            if (element.type == 'checkbox') {
                if (element.checked) {
                    searchValues[element.name] = element.value;
                }
            }
            else
            {
                searchValues[element.name] = element.value;
            }
        }
    }
    return searchValues;
}

Object.size = function (obj) {
    var size = 0, key;
    for (key in obj) {
        if (obj.hasOwnProperty(key)) {
            size++;
        }
    }
    return size;
};

function trim(str)
{
    return str.replace(/^\s\s*/, '').replace(/\s\s*$/, '');
}

function addRemoveElement(toChangeID, buttonID, description, plusMinusOptions)
{
    if (plusMinusOptions)
    {
        hideValue = plusMinusOptions.split('|')[0]        
        showValue = plusMinusOptions.split('|')[1]
    }
    else
    {
        hideValue = '-'        
        showValue = '+'
    }

    var plusOrMinus = trim(document.getElementById(buttonID).innerHTML);
    if(plusOrMinus==showValue)
    {
        document.getElementById(buttonID).innerHTML = hideValue;
        document.getElementById(toChangeID).style.display="block";
        document.getElementById(toChangeID).style.visibility="visible";
        document.getElementById(buttonID).title = 'hide ' + description;
    }
    else
    {
        document.getElementById(buttonID).innerHTML = showValue;
        document.getElementById(buttonID).title = 'show ' + description;
        document.getElementById(toChangeID).style.display="none";
    }
}

function confirmDelete(entityType, entityID)
{
    var decision = confirm('Are you sure you want to delete ' + entityType + ' ' + entityID + '?');
    if (decision) {
        return true;
    }
    else {
        return false;
    }
}

function hideReveal(patientID)
{
    var patient = document.getElementById(patientID);
    if (patient.style.visibility == "hidden")
    {
        patient.style.visibility = "visible";
        patient.style.display = "block";
    }
    else
    {
        patient.style.visibility = "hidden";
        patient.style.display = "none";
    }
}

function showHide(id){
    var div = document.getElementById(id);
    if (div.style.visibility=='visible'){
        div.style.visibility = 'hidden';
        div.style.display = 'none';
    }
    else {
        div.style.visibility = 'visible';
        div.style.display = 'block';
    }
}

function hide(patientID)
{
    var patient = document.getElementById(patientID);
    patient.style.visibility = "hidden";
    patient.style.display = "none";
}

function reveal(patientID)
{
    var patient = document.getElementById(patientID);
    patient.style.visibility = "visible";
    patient.style.display = "block";
}



function createFormActionButton(formID, uniqueNo, updateURL, historyURL,
        associateURL, rememberURL, exportURL, deleteURL, duplicateURL, disassociateURL)
{
    var id = 'form' + formID + '_' + uniqueNo;
    var menuID = id + 'Menu';
    var menuDivID = id + 'MenuDiv';
    var viewMenuID = id + 'ViewMenu';
    var formSubmenuID = id + 'SubmenuDiv';
    var additionalDataButtonID = id + 'AdditionalDataButton';
    var additionalDataDivID = id + 'AdditionalDataDiv';
    var associatedFilesButtonID = id + 'AssociatedFilesButton';
    var associatedFilesDivID = id + 'AssociatedFilesDiv';
    var deleteID = id + 'Delete';
    var formTranscriptionTDID = id + 'transcription';

    var viewItemData = [{text: "Additional Data", id: additionalDataButtonID}];
    var itemdataRest = [
        {text: "Update", url: updateURL},
        {text: "Associate", url: associateURL},
        {text: "Remember", url: rememberURL},
        {text: "Export", url: exportURL},
        {text: "Delete", id: deleteID},
        {text: "Duplicate", url: duplicateURL}
    ];

    if (disassociateURL === undefined){
        viewItemData.push({text: "Associated Files", id: associatedFilesButtonID});
        } else {
            var disassociateID = id + 'Disassociate';
            itemdataRest.push({text: "Disassociate", url: disassociateURL})
        }

    viewItemData.push({text: "History", url: historyURL});

    YAHOO.util.Event.onAvailable(menuDivID, function () {
        var x = [
            {
                text: "+",
                submenu: {
                    id: formSubmenuID,
                    itemdata: [
                        {
                            text: "View",
                            submenu: {
                                id: viewMenuID,
                                itemdata: viewItemData
                            }
                        }
                    ].concat(itemdataRest)
                }
            }
        ]
        var oMenu = new YAHOO.widget.MenuBar(menuID, {
            autosubmenudisplay: true});
        oMenu.addItems(x);
        oMenu.render(menuDivID);

        showHideAdditionalData = function () {showHide(additionalDataDivID);}
        additionalDataButton = document.getElementById(additionalDataButtonID);
        YAHOO.util.Event.addListener(
            additionalDataButton,
            "click",
            showHideAdditionalData
        );

        showHideAssociatedFiles = function () {showHide(associatedFilesDivID);}
        associatedFilesButton = document.getElementById(associatedFilesButtonID);
        YAHOO.util.Event.addListener(
            associatedFilesButton,
            "click",
            showHideAssociatedFiles
        );

        // Link Form transcription td to an action which reveals all data
        var showEverything = function () {
            showHide(additionalDataDivID);
            if (document.getElementById(associatedFilesDivID) != null) {
                showHide(associatedFilesDivID);
            }
        }
        var formTranscriptionTD = document.getElementById(formTranscriptionTDID);
        YAHOO.util.Event.addListener(
            formTranscriptionTD,
            "click",
            showEverything
        );

        // Confirm dialog box for delete action
        deleteElement = document.getElementById(deleteID);
        YAHOO.util.Event.addListener(
            deleteElement, "click",
            function (){
                var decision = confirm(
                    'Are you sure you want to delete Form ' + formID + '?');
                if (decision){ window.location = deleteURL; }
            }
        );

        // Disassociate button
        if (disassociateURL !== undefined){
            disassociateElement = document.getElementById(disassociateID);
            YAHOO.util.Event.addListener(
                disassociateElement, "click",
                function (){ window.location = disassociateURL; }
            );
        }
    });
}




function createFileActionButton(fileID, uniqueNo, updateURL, associateURL,
                                deleteURL, disassociateURL) {
    var id = 'file' + fileID + '_' + uniqueNo;
    var menuID = id + 'Menu';
    var menuDivID = id + 'MenuDiv';
    var viewMenuID = id + 'ViewMenu';
    var fileSubmenuID = id + 'SubmenuDiv';
    var mediaButtonID = id + 'MediaButton';
    var mediaDivID = id + 'MediaDiv';
    var additionalDataButtonID = id + 'AdditionalDataButton';
    var additionalDataDivID = id + 'AdditionalDataDiv';
    var associatedFormsButtonID = id + 'AssociatedFormsButton';
    var associatedFormsDivID = id + 'AssociatedFormsDiv';
    var deleteID = id + 'Delete';
    var fileNameAnchorID = id + 'NameAnchor';
    var itemdata = [
                        {
                            text: "View",
                            submenu: {
                                id: viewMenuID,
                                itemdata: [
                                    {text: "File Media",
                                        id: mediaButtonID},
                                    {text: "Additional Data",
                                        id: additionalDataButtonID},
                                    {text: "Associated Forms",
                                        id: associatedFormsButtonID}
                                ]
                            }
                        },
                        {text: "Update", url: updateURL},
                        {text: "Associate", url: associateURL},
                        {text: "Delete", id: deleteID}
                    ]
    if (disassociateURL !== undefined) {
        var disassociateID = id + 'Disassociate';
        itemdata.push({text: "Disassociate", id: disassociateID});
    }

    YAHOO.util.Event.onAvailable(menuDivID, function () {
        var x = [
            {
                text: "+",
                submenu: {
                    id: fileSubmenuID,
                    itemdata: itemdata
                }
            }
        ]
        var oMenu = new YAHOO.widget.MenuBar(menuID, {
            autosubmenudisplay: true});
        oMenu.addItems(x);
        oMenu.render(menuDivID);

        // Button to reveal File media
        showHideMediaDiv = function () {showHide(mediaDivID);}
        mediaButton = document.getElementById(mediaButtonID);
        YAHOO.util.Event.addListener(
            mediaButton,
            "click",
            showHideMediaDiv
        );

        // Button to reveal additional data
        showHideAdditionalDataDiv = function () {
            showHide(additionalDataDivID);}
        additionalDataButton = document.getElementById(additionalDataButtonID);
        YAHOO.util.Event.addListener(
            additionalDataButton,
            "click",
            showHideAdditionalDataDiv
        );

        // Button to reveal associated Forms
        showHideAssociatedFormsDiv = function () {
            showHide(associatedFormsDivID);}
        associatedFormsButton = document.getElementById(
                                                    associatedFormsButtonID);
        YAHOO.util.Event.addListener(
            associatedFormsButton,
            "click",
            showHideAssociatedFormsDiv
        );

        // Link name anchor of the File to actions which reveal all data
        var showEverything = function () {
            showHide(mediaDivID);
            showHide(additionalDataDivID);
            showHide(associatedFormsDivID);
        }
        var fileNameAnchor = document.getElementById(fileNameAnchorID);
        YAHOO.util.Event.addListener(
            fileNameAnchor,
            "click",
            showEverything
        );

        // Confirm dialog for deleting of Files
        deleteElement = document.getElementById(deleteID);
        YAHOO.util.Event.addListener(
            deleteElement, "click",
            function (){
                var decision = confirm(
                    'Are you sure you want to delete File ' + fileID + '?');
                if (decision){ window.location = deleteURL; }
            }
        );

        // Disassociate button, if needed
        if (disassociateURL !== undefined) {
            disassociateElement = document.getElementById(disassociateID);
            YAHOO.util.Event.addListener(
                disassociateElement, "click",
                function (){
                    window.location = disassociateURL;
                }
            );
        }
    });

}


// saveUserDisplaySetting makes an Ajax call to /researcher/saveuserdisplaysetting
//  and saves the display value of elementID to the user's server-side settings.
var saveUserDisplaySetting = function (elementID) {
    var visibility = document.getElementById(elementID).style.visibility;
    var valueMap = {visible: "false", hidden: "true"};
    var value = valueMap[visibility] || "false";
    var settingMap = {
        narrowPhoneticTranscriptionLI: 'displayNarrowPhoneticTranscriptionField',
        phoneticTranscriptionLI: 'displayBroadPhoneticTranscriptionField'};
    var setting = settingMap[elementID];
    var parameters = "setting=" + setting + "&value=" + value;

    var responseSuccess = function(o) {
        console.log(o.responseText);
    }

    var responseFailure = function(o) {};

    var callback = {
        success: responseSuccess,
        failure: responseFailure
    };

    var sUrl = '/researcher/saveuserdisplaysetting';
    var transaction = YAHOO.util.Connect.asyncRequest(
                                'POST', sUrl, callback, parameters);
};



// This is the action button on the form add/update page that toggles the
//  phonetic transcription fields 
function createFormAddActionButton() {
    var menuDivID = "addUpdateFormMenuDivID";
    
    YAHOO.util.Event.onAvailable(menuDivID, function () {
        var menuID = "addUpdateFormMenuID";
        var narrPhonID = "narrowPhoneticTranscriptionLI";
        var narrPhonButtonID = "narrowPhoneticTranscriptionButton";
        var broadPhonID = "phoneticTranscriptionLI";
        var broadPhonButtonID = "broadPhoneticTranscriptionButton";
        var menu = [
            {
                text: "+",
                submenu: {
                    id: "fileSubmenuID",
                    itemdata: [
                        {
                            text: "Narrow phonetic transcription",
                            id: narrPhonButtonID
                        },
                        {
                            text: "Broad phonetic transcription",
                            id: broadPhonButtonID
                        }
                    ]
                }
            }
        ];
        var oMenu = new YAHOO.widget.MenuBar(menuID, {
            autosubmenudisplay: true});
        oMenu.addItems(menu);
        oMenu.render(menuDivID);

        // Bind the clicking of the narrow phon menu item to a function that
        //  toggles the field's display and asynchronously saves the setting
        var toggleNarrPhon = function () {
            // Ajax call to save the setting
            saveUserDisplaySetting(narrPhonID);
            showHide(narrPhonID);
        };
        var narrPhonButton = document.getElementById(narrPhonButtonID);
        YAHOO.util.Event.addListener(
            narrPhonButton,
            "click",
            toggleNarrPhon
        );

        // Bind the clicking of the broad phon menu item to a function that
        //  toggles the field's display and asynchronously saves the setting
        var toggleBroadPhon = function () {
            // Ajax call
            saveUserDisplaySetting(broadPhonID);
            showHide(broadPhonID);
        };
        var broadPhonButton = document.getElementById(broadPhonButtonID);
        YAHOO.util.Event.addListener(
            broadPhonButton,
            "click",
            toggleBroadPhon
        );
        
    });

}


// Function retrieves all .term elements and binds their click event to the
//  toggling of their sibling .explanation elements.
var bindTermClickToExplanationToggle = function () {
    $(".term").each(function () {
        $(this).click(function () {
            $($(this).siblings(['.explanation'])).toggle('slow');
        });
    });
};

var hideAllExplanations = function () {
    $(".explanation").hide();
}


// getCodePoints returns the unicode code points of the input unistr formated as
//  "U+0097, U+0301"
var getCodePoints = function (unistr) {
    var pad = function (hexString) {
        var key = {1: '000', 2: '00', 3: '0'};
        if (key[hexString.length]) {
            return key[hexString.length] + hexString;}
        return hexString;
    };
    var result = [];
    for (var i = 0; i < unistr.length; i ++) {
        result.push("U+" + pad(unistr.charCodeAt(i).toString(16).toUpperCase()));
    }
    return result.join(", ");
}