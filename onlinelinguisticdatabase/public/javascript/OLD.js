////////////////////////////////////////////////////////////////////////////////
// OLD -- Online Linguistic Database
////////////////////////////////////////////////////////////////////////////////

var OLD = {};
OLD.forms = {};
OLD.pages = {}; // Holds Page objects


////////////////////////////////////////////////////////////////////////////////
// UTILITY FUNCTIONS
////////////////////////////////////////////////////////////////////////////////


// Beget method of Object
//  Cf. Douglas Crockford's "Javascript: the Good Parts", section 3.5 Prototype
if (typeof Object.beget !== 'function') {
    Object.beget = function (o) {
        var F = function () {};
        F.prototype = o;
        return new F();
    };
}


// Get Function From data-function Attribute
//  takes the value of an HTML data-function attribute and returns a method of
//  an object of OLD: e.g., data-function="forms.getAddInterface" returns
//  OLD.forms.getAddInterface
OLD.getFunctionFromDataFunctionAttribute = function (dfVal) {
    var key = dfVal.split('.')[0];
    var meth = dfVal.split('.')[1];
    if (meth) {
        return this[key][meth];
    } else {
        return this[key];
    }
}


// Bind Function to Keyboard Shortcut
//  Takes the value of an HTML data-shortcut attribute and uses it to create a
//  keyboard shortcut to the function referenced in the data-function attribute.
OLD.bindFunctionToKeyboardShortcut = function (functionString, shortcutString) {

    // Get the function to call on the keydown event
    var func = this.getFunctionFromDataFunctionAttribute(functionString);

    // Mapper returns an object, e.g., {ctrlKey: true, shortcutKey: 65}
    var mapper = OLD.getShortcutMapper(shortcutString);

    // Bind the keydown event to the function
    $(document).keydown(function (event) {
        if ((event.ctrlKey === mapper.ctrlKey) &&
            (event.altKey === mapper.altKey) &&
            (event.shiftKey === mapper.shiftKey) &&
            (event.which === mapper.shortcutKey))
            func();
    });
}


// Get Shortcut Mapper
//  Takes a shortcutString (e.g., 'ctrl+a') and returns an object of the form
//  {ctrlKey: true, shortcutKey: 65}
OLD.getShortcutMapper = function (shortcutString) {
    var shortcutArray = shortcutString.split('+');

    // Returns the codes for the arrow symbols or alse the character code
    function getShortcutCode(shortcutAsString) {
        if (shortcutAsString === 'rArrow')
            return 39;
        else if (shortcutAsString === 'lArrow')
            return 37;
        else if (shortcutAsString === 'uArrow')
            return 38;
        else if (shortcutAsString === 'dArrow')
            return 40;
        else
            return shortcutAsString.toUpperCase().charCodeAt(0);
    }

    return {
        ctrlKey: shortcutArray.indexOf('ctrl') !== -1,
        altKey: shortcutArray.indexOf('alt') !== -1,
        shiftKey: shortcutArray.indexOf('shift') !== -1,
        shortcutKey: getShortcutCode(shortcutArray.pop())
    }
}

// Get Shortcut Abbreviation
//  E.g., from "ctrl+a" return "\u2303A", from "alt+rArrow" return "\u2325\u2192"
OLD.getShortcutAbbreviation = function (shortcutString) {
    var shortcutArray = shortcutString.split('+');

    // Return an abbreviation of the shortcut key
    function getShortcutKeyAbbrev(shortcutString) {
        if (shortcutString === 'rArrow')
            return "\u2192";
        else if (shortcutString === 'lArrow')
            return "\u2190";
        else if (shortcutString === 'uArrow')
            return "\u2191";
        else if (shortcutString === 'dArrow')
            return "\u2193";
        else
            return shortcutString[0].toUpperCase();
    }

    // Get meta characters and shortcut key in an ordered list
    var symbols = [
        ctrlSym = (shortcutArray.indexOf('ctrl') === -1) ? "": "\u2303",
        altSym = (shortcutArray.indexOf('alt') === -1) ? "": "\u2325",
        shiftSym = (shortcutArray.indexOf('shift') === -1) ? "": "\u21E7",
        shortcutSym = getShortcutKeyAbbrev(shortcutArray.pop())
    ]

    return symbols.join('');
}


// Bind Keyboard Shortcut to Click
//  Takes a wrapped set of elements containing 'data-shortcut' attributes and
//  binds the encoded keyboard shortcut to each element's click event
//  This method permits the easy creation of keyboard shortcuts to any button
//  just by specifying a data-shortcut attribute.
OLD.bindKeyboardShortcutToClick = function (wrappedSet) {
    // Remember the shortcuts we've bound so we don't repeat
    var boundShortcuts = [];

    // Unbind previously registered keyboard-shortcut-2-click handlers so we
    //  don't create duplicate handlers
    $(document).unbind('.kbShortcut2Click');

    wrappedSet.each(function (index, element) {
        var shortcutString = $(this).attr('data-shortcut')

        // Get the shortcut abbreviation and append it to the title attribute
        var shortcutAbbreviation = OLD.getShortcutAbbreviation(shortcutString);
        $(this).attr('title', $(this).attr('title') + ' ' +
                     shortcutAbbreviation);

        // Only bind the keyboard event to the click event if we have not seen
        //  this keyboard shortcut before
        if (boundShortcuts.indexOf(shortcutString) === -1) {

            // Remember having seen this shortcut
            boundShortcuts.push(shortcutString); 

            var clicker = function () {
                // Only click the button if it is not disabled
                if ($(element).attr('disabled') !== 'disabled')
                    $(element).click();
            }

            // Mapper returns an object, e.g., {ctrlKey: true, shortcutKey: 65}
            var mapper = OLD.getShortcutMapper(shortcutString);

            // Bind the keydown event to the click event
            $(document).bind('keydown.kbShortcut2Click',
                             function (event, button) {
                if ((event.ctrlKey === mapper.ctrlKey) &&
                    (event.altKey === mapper.altKey) &&
                    (event.shiftKey === mapper.shiftKey) &&
                    (event.which === mapper.shortcutKey)) {
                    event.preventDefault();
                    clicker();
                }
            });
        }
    });
}


// Remove Form Tabbing handlers
OLD.removeFormTabbingHandlers = function () {
    $(document).unbind('.formTabbing');
}


// Clean the DOM of unnecessary widgets & event handlers
OLD.cleanDOM = function () {
    OLD.removeExplanations();
    OLD.closeLoginDialogBox();
    OLD.removeFormTabbingHandlers();
}


// OLD Page constructor
//  The prototype for all OLD pages.
//  params expects minimally a url property
OLD.Page = function (params) {
    this.params = params || {};

    // Display
    this.display = function (params) {
        $.extend(this.params, params);
        this.params.url = this.params.url || null;
        if (this.params.url) {
            console.log('requesting data');
            this.requestData();
        } else {
            this.setContent();
            this.write();
        }
    };

    // Write -- write the page content to the DOM
    this.write = function () {
        OLD.cleanDOM();
        this.setPageDiv();
        this.pageDiv.html(this.content);
    };

    // Request Data
    this.requestData = function (params) {
        $.extend(this.params, params);
        this.params.requestParams = this.params.requestParams || null;
        this.params.callback = $.proxy(this.handleResponse, this);
        this.params.responseType = this.params.responseType || 'json';

        OLD.showSpinner();
        $.get(this.params.url, this.params.requestParams,
              this.params.callback, this.params.responseType);
    };

    // Handle Response
    this.handleResponse = function (response, statusText) {
        OLD.hideSpinner();
        this.params.response = response;
        if (statusText === "success") {
            if (response === "unauthenticated") {
                console.log('Authentication failure');
                OLD.openLoginDialogBox();
            } else if (response === "unauthorized") {
                console.log('Authorization failure');
            } else {
                $.extend(this.params, response);
                this.updateFormCount();
                this.setContent();
                this.write();
            }
        } else {
            console.log('Ajax request failure.');
        }
    };

    // Update Form Count
    this.updateFormCount = function () {
        if (this.params.formCount) {
            OLD.formCount = this.params.formCount;
        }
    };

    // Set Content
    this.setContent = function () {

        this.setPageHeader();
        this.setPageBody();

        this.content = $('<div>')
            .append(this.pageHeader.getContent())
            .append(this.pageBody.getContent())
            .children();
    };

    // Set Page Div
    this.setPageDiv = function () {
        this.pageDiv = $('#old-page');
    };

    // Get Page Div
    this.getPageDiv = function () {
        return this.pageDiv;
    };

    // Set Page Header
    this.setPageHeader = function () {
        var params = {titleText:
            (this.params.headerText) ? this.params.headerText : undefined};
        this.pageHeader = new OLD.PageHeader(params);
    };

    // Get Page Header
    this.getPageHeader = function () {
        return this.pageHeader;
    };

    // Set Page Body
    this.setPageBody = function () {
        var params = (this.params.bodyContent !== undefined) ?
                      {bodyHTML: this.params.bodyContent} : {};
        this.pageBody = new OLD.PageBody(params);
    };

    // Get Page Body
    this.getPageBody = function () {
        return this.pageBody;
    };

    // Get Content
    this.getContent = function () {
        return this.content;
    };
};


// OLD Page Header constructor
//  Use this to create page header objects.
OLD.PageHeader = function (params) {
    this.params = params || {};

    // Set Title Div
    this.setTitleDiv = function (titleText) {
        var title = titleText || this.params.titleText || 'OLD Page Header';
        var formCount = OLD.formCount ? ' (' + OLD.formCount + ' Forms)' : '';
        title = title + formCount;
        this.titleDiv = $('<div>').addClass('old-page-header-title')
                            .text(title);
    };

    // Get Title Div
    this.getTitleDiv = function () {
        return this.titleDiv;
    };

    // Set Widgets Div
    this.setWidgetsDiv = function (widgetsHTML) {
        var widgets = widgetsHTML || this.params.widgetsHTML || '';
        this.widgetsDiv = $('<div>').addClass('old-page-header-widgets')
                        .append(widgets);
    };

    // Get Widgets Div
    this.getWidgetsDiv = function () {
        return this.widgetsDiv;
    };

    // Set Content
    this.setContent = function () {
        this.content = $('<div>')
            .addClass('old-page-header ui-widget-header ui-corner-top')
            .append(this.titleDiv)
            .append(this.widgetsDiv);
    };

    // Get Content
    this.getContent = function () {
        return this.content;
    };

    // Initialize
    this.init = function () {
        this.setTitleDiv();
        this.setWidgetsDiv();
        this.setContent();
    };
    this.init();
};

// OLD Page Body constructor
//  Use this to create page body objects.
OLD.PageBody = function (params) {
    this.params = params || {};

    // Set Content
    this.setContent = function (bodyHTML) {
        var contentHTML = bodyHTML || this.params.bodyHTML || '';
        this.content = $('<div>').addClass('old-page-body').html(contentHTML);
    };

    // Get Content
    this.getContent = function () {
        return this.content;
    };

    // Initialize
    this.init = function () {
        this.setContent();
    };
    this.init();
};


OLD.AddFormPage = function (params) {
};

OLD.AddFormPage.prototype = new OLD.Page();

OLD.AddFormPageBody = function (params) {

    // Set Content
    this.setContent = function (bodyHTML) {
        
        // Used to have the class "old-forms-add-interface"
        this.content = $('<div>').addClass('old-page-body')
            .html($('div.template.formAddForm').children().clone());

        // Populate the options of the select fields, e.g., speakers
        this.populateSelectFields();

        // Enable button to add new gloss fields
        OLD.forms.enableAddNewGlossFieldButton(body);
    
        // UI stuff: selectmenus, buttons
        $('select.grammaticality', body).selectmenu({width: 50});
        $('button.insertGlossFieldButton', body)
            .button({icons: {primary: 'ui-icon-plus'}, text: false});
        $('input[type="submit"]', body).button()
        $('select[name="elicitationMethod"]', body).selectmenu({width: 548});
        $('select[name="keywords"]', body).hide();
        $('select[name="syntacticCategory"]', body).selectmenu({width: 548});
        $('select[name="speaker"]', body).selectmenu({width: 548});
        $('select[name="elicitor"]', body).selectmenu({width: 548});
        $('select[name="verifier"]', body).selectmenu({width: 548});
        $('select[name="source"]', body).selectmenu({width: 548});
        $('input[name="dateElicited"]', body).datepicker(
            {appendText: "<span style='margin: 0 10px;'>mm/dd/yyyy</span>",
             autoSize: true});
        $('select, input, textarea', body)
            .css("border-color", OLD.jQueryUIColors.defBo);
        $('textarea.transcription', body)
            .focus(function () {window.scrollTo(0, 0);});
    
        // Submit Form data functionality
        
        // CTRL + <Return> in the form submits the form
        $('form.formAdd', body).keydown(function (event) {
            if (event.ctrlKey && event.which === 13) {
                event.preventDefault();
                $('input[type="submit"]', this).click();
            }
        });
    
        // <Return> in a text input submits the form
        $('form.formAdd input[type="text"]', body)
            .keydown(function (event) {
                if (event.which === 13) {
                    event.preventDefault();
                    $('form.formAdd input[type="submit"]', body).click();
                }
            });
    
        // Handle the response from the form/add_ajax controller action
        function handleResponse(responseJSON) {
            OLD.hideSpinner();
            if (responseJSON.valid) {
                OLD.forms.displayForm(responseJSON.form);
            } else {
                // Re-enable the submit button
                $('form.formAdd input[type="submit"]', body)
                    .attr('disabled', false);
    
                // Display the invalid field inputs
                OLD.displayValidationErrors(responseJSON.errors, body);
            }
        }
    
        // Handle an error in the server response
        function handleError(jqXHR, exception){
            OLD.hideSpinner();
            alert('Response error: ' + jqXHR.status + ' | ' + exception);
        }
    
        // Show the request to the server (for debugging purposes)
        function showRequest(formData, jqForm, options) { 
            var queryString = $.param(formData); 
            alert('About to submit: \n\n' + queryString);
        }
    
        // Define the submit action
        $('form.formAdd', body).submit(function (event) {
            OLD.showSpinner();
    
            // Remove any validation error widgets
            $('.old-val-err-widget', body).remove();
            $('input[type="submit"]', this).attr('disabled', 'disabled');
            $(this).ajaxSubmit({success: handleResponse,
                                dataType: 'json',
                                error: handleError});
            return false;
        });
    
        return addInterface.append(header).append(body);

    };


    // Populate Select Fields of the Add Form Interface
    //  populates the select fields of the Add Form interface with options
    //  received from the server via an asynchronous request.
    this.populateSelectFields = function () {
        $.get('form/get_form_options_ajax', null, updateAddInterface, 'json');

        function updateAddInterface(formAddOptions, statusText) {
            if (statusText === "success") {
                // Save the formAddOptions for later,
                //  e.g., for additional gloss grammaticality select fields
                OLD.forms.formAddOptions = formAddOptions;
    
                // Populate grammaticality
                $.each(formAddOptions.grammaticalities, function () {
                    $('select.grammaticality', context)
                        .append($('<option>').attr('value', this[0]).text(this[0]));
                });
                $('select.grammaticality', context).selectmenu({width: 50});
    
                // Populate elicitationMethod
                $.each(formAddOptions.elicitationMethods, function () {
                    $('select[name="elicitationMethod"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('select[name="elicitationMethod"]', context).selectmenu();
    
                // Populate keywords
                $.each(formAddOptions.keywords, function () {
                    $('select[name="keywords"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('.keywordsMultiselect', context).remove();
                $('select[name="keywords"]', context)
                    .multiselect({minWidth: 550, classes: "keywordsMultiselects",
                        close: function () {
                            $('select[name="syntacticCategory"]', context)
                                .focus();
                        }
                    });
    
                // Populate category
                $.each(formAddOptions.categories, function () {
                    $('select[name="syntacticCategory"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('select[name="syntacticCategory"]', context).selectmenu();
    
                // Populate speaker
                $.each(formAddOptions.speakers, function () {
                    $('select[name="speaker"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('select[name="speaker"]', context).selectmenu();
    
                // Populate elicitor & verifier
                $.each(formAddOptions.users, function () {
                    $('select[name="elicitor"], select[name="verifier"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('select[name="elicitor"]', context).selectmenu();
                $('select[name="verifier"]', context).selectmenu();
    
                // Populate source
                $.each(formAddOptions.sources, function () {
                    $('select[name="source"]', context)
                        .append($('<option>').attr('value', this[0]).text(this[1]));
                });
                $('select[name="source"]', context).selectmenu();
            }
        }
    };



};


////////////////////////////////////////////////////////////////////////////////
// Secondary Object Stores
////////////////////////////////////////////////////////////////////////////////

//grammaticalities, elicitation methods, keywords, categories, speakers, users,
//sources -- I want to keep a local store of these objects.  I also want to min-
//imize network traffic and db lookups while staying current ...

// Secondary Object Store
//  Constructor for ...
OLD.SecondaryObjectStore = function () {

    this.items = [];

    // Set Items
    this.setItems = function () {
        var items = this.getItems();
        if (items.length === 0) {
            
        } else {
            
        }
    };

    this.getItems = function () {
        return this.items;
    };
};

OLD.GrammaticalitiesStore = function () {};
OLD.ElicitationMethodsStore = function () {};
OLD.KeywordsStore = function () {};
OLD.CategoriesStore = function () {};
OLD.SpeakersStore = function () {};
OLD.UsersStore = function () {};
OLD.SourcesStore = function () {};


// Display Add Interface (for adding new Forms)
OLD.forms.displayAddInterface = function () {
    OLD.getPage().html(OLD.forms.getAddInterface())
        .find('textarea')[0].focus();
    $('#old-page textarea').elastic({compactOnBlur: false});
}


// Get Form Add Interface
OLD.forms.getAddInterface = function () {
    var addInterface = $('<div>').addClass('old-forms-add-interface');
    var header = OLD.getPageHeader('Add a Form');
    var body = OLD.getPageBody()
                    .html($('div.template.formAddForm').children().clone());

    // Populate the options of the select fields, e.g., speakers
    OLD.forms.populateAddInterfaceSelectFields(body);

    // Enable button to add new gloss fields
    OLD.forms.enableAddNewGlossFieldButton(body);

    // UI stuff: selectmenus, buttons
    $('select.grammaticality', body).selectmenu({width: 50});
    $('button.insertGlossFieldButton', body)
        .button({icons: {primary: 'ui-icon-plus'}, text: false});
    $('input[type="submit"]', body).button()
    $('select[name="elicitationMethod"]', body).selectmenu({width: 548});
    $('select[name="keywords"]', body).hide();
    $('select[name="syntacticCategory"]', body).selectmenu({width: 548});
    $('select[name="speaker"]', body).selectmenu({width: 548});
    $('select[name="elicitor"]', body).selectmenu({width: 548});
    $('select[name="verifier"]', body).selectmenu({width: 548});
    $('select[name="source"]', body).selectmenu({width: 548});
    $('input[name="dateElicited"]', body).datepicker(
        {appendText: "<span style='margin: 0 10px;'>mm/dd/yyyy</span>",
         autoSize: true});
    $('select, input, textarea', body)
        .css("border-color", OLD.jQueryUIColors.defBo);
    $('textarea.transcription', body)
        .focus(function () {window.scrollTo(0, 0);});

    // Submit Form data functionality
    
    // CTRL + <Return> in the form submits the form
    $('form.formAdd', body).keydown(function (event) {
        if (event.ctrlKey && event.which === 13) {
            event.preventDefault();
            $('input[type="submit"]', this).click();
        }
    });

    // <Return> in a text input submits the form
    $('form.formAdd input[type="text"]', body)
        .keydown(function (event) {
            if (event.which === 13) {
                event.preventDefault();
                $('form.formAdd input[type="submit"]', body).click();
            }
        });

    // Handle the response from the form/add_ajax controller action
    function handleResponse(responseJSON) {
        OLD.hideSpinner();
        if (responseJSON.valid) {
            OLD.forms.displayForm(responseJSON.form);
        } else {
            // Re-enable the submit button
            $('form.formAdd input[type="submit"]', body)
                .attr('disabled', false);

            // Display the invalid field inputs
            OLD.displayValidationErrors(responseJSON.errors, body);
        }
    }

    // Handle an error in the server response
    function handleError(jqXHR, exception){
        OLD.hideSpinner();
        alert('Response error: ' + jqXHR.status + ' | ' + exception);
    }

    // Show the request to the server (for debugging purposes)
    function showRequest(formData, jqForm, options) { 
        var queryString = $.param(formData); 
        alert('About to submit: \n\n' + queryString);
    }

    // Define the submit action
    $('form.formAdd', body).submit(function (event) {
        OLD.showSpinner();

        // Remove any validation error widgets
        $('.old-val-err-widget', body).remove();
        $('input[type="submit"]', this).attr('disabled', 'disabled');
        $(this).ajaxSubmit({success: handleResponse,
                            dataType: 'json',
                            error: handleError});
        return false;
    });

    return addInterface.append(header).append(body);
}



// Populate Form Add Interface Select Fields
//  populates the select fields of the Add Form interface with options received
//  from the server via Ajax
OLD.forms.populateAddInterfaceSelectFields = function (context) {
    $.get('form/get_form_options_ajax', null, updateAddInterface, 'json');

    function updateAddInterface(formAddOptions, statusText) {
        if (statusText === "success") {
            // Save the formAddOptions for later,
            //  e.g., for additional gloss grammaticality select fields
            OLD.forms.formAddOptions = formAddOptions;

            // Populate grammaticality
            $.each(formAddOptions.grammaticalities, function () {
                $('select.grammaticality', context)
                    .append($('<option>').attr('value', this[0]).text(this[0]));
            });
            $('select.grammaticality', context).selectmenu({width: 50});

            // Populate elicitationMethod
            $.each(formAddOptions.elicitationMethods, function () {
                $('select[name="elicitationMethod"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('select[name="elicitationMethod"]', context).selectmenu();

            // Populate keywords
            $.each(formAddOptions.keywords, function () {
                $('select[name="keywords"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('.keywordsMultiselect', context).remove();
            $('select[name="keywords"]', context)
                .multiselect({minWidth: 550, classes: "keywordsMultiselects",
                    close: function () {
                        $('select[name="syntacticCategory"]', context)
                            .focus();
                    }
                });

            // Populate category
            $.each(formAddOptions.categories, function () {
                $('select[name="syntacticCategory"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('select[name="syntacticCategory"]', context).selectmenu();

            // Populate speaker
            $.each(formAddOptions.speakers, function () {
                $('select[name="speaker"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('select[name="speaker"]', context).selectmenu();

            // Populate elicitor & verifier
            $.each(formAddOptions.users, function () {
                $('select[name="elicitor"], select[name="verifier"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('select[name="elicitor"]', context).selectmenu();
            $('select[name="verifier"]', context).selectmenu();

            // Populate source
            $.each(formAddOptions.sources, function () {
                $('select[name="source"]', context)
                    .append($('<option>').attr('value', this[0]).text(this[1]));
            });
            $('select[name="source"]', context).selectmenu();
        }
    }
}



// Enable the Form Add Interface's Insert New Gloss Field Button
//  I.e., bind its click event to the creation of new gloss fields
OLD.forms.enableAddNewGlossFieldButton = function(context) {
    $('button.insertGlossFieldButton', context)
        .data('glossFieldCount', 0)
        .click(function (event) {
            event.preventDefault();
            $(this).data('glossFieldCount', $(this).data('glossFieldCount') + 1);
            var name = 'glosses-' + $(this).data('glossFieldCount');
            $('<li>').appendTo($(this).closest('ul')).hide()
                .addClass("newGloss")
                .data('index', $(this).data('glossFieldCount'))
                .append($('<label>').attr('for', name + '.gloss').text('Gloss'))
                .append($('<select>').attr({name: name + '.grammaticality',
                    tabindex: '1'}).addClass('grammaticality'))
                .append($('<textarea>').attr({name: name + '.gloss',
                        maxlength: '255', tabindex: '1'})
                        .addClass('gloss')
                        .css("border-color", OLD.jQueryUIColors.defBo))
                .append($('<button>').addClass('removeMe')
                    .attr({title: 'Remove this gloss field.', tabindex: '1'})
                    .text('Remove Me')
                    .button({icons: {primary: 'ui-icon-minus'}, text: false})
                    .focus(function () {$(this).addClass('ui-state-focus')})
                    .blur(function () {$(this).removeClass('ui-state-focus')}))
                .slideDown('slow');
            $.each(OLD.forms.formAddOptions.grammaticalities, function () {
                $('[name="' + name + '.grammaticality"]')
                    .append($('<option>').attr('value', this[0]).text(this[0]));
            });
            $('[name="' + name + '.grammaticality"]').selectmenu({width: 50});
            $('[name="' + name + '.gloss"]').elastic({compactOnBlur: false});
            $('button.removeMe').click(function (event) {
                event.preventDefault();
                $(this).closest('li').prev('li').find('textarea').focus();
                $(this).closest('li').slideUp('slow', function () {
                    $(this).remove()});
            });
        });
}







// Items Per Page Selector constructor (for paginator pages)
//  Used to change how many items are displayed in a pagination page
//  The paginator parameter holds crucial first_item and items_per_page data
//  paginatorRequestor is the method that requests a new page (e.g., browse)
//  objectName (e.g., 'form') is required to get the appropriate user setting
OLD.getItemsPerPageSelector = function (paginator, paginatorRequestor,
                                        objectName) {

    // Get relevant xItemsPerPage from userSettings, based on objectName
    var itemsPerPage = OLD.userSettings[objectName + 'ItemsPerPage'];

    // Build the select element
    function conjug(n) {return (n === 1) ? '' : 's';}
    var select = $('<select>').addClass('old-pagin-ipp-select');
    $.each(OLD.applicationSettings.itemsPerPageOptions, function (index, item) {
        select.append($('<option>')
            .text(item + ' item' + conjug(item) + ' per page')
            .attr({'value': this, 'selected': (item === itemsPerPage)}));
    });

    // Bind the select's change event to a request for a new page with the new
    //  items_per_page argument
    select.change(function () {
        OLD.userSettings[objectName + 'ItemsPerPage'] = parseInt($(this).val());
        paginatorRequestor({items_per_page: parseInt($(this).val())});
    })

    // Return the select wrapped in a centered div
    //return $('<div>').addClass('old-pagin-ipp').append(select);
    return select;
}

// Paginate Navigator: stylized interface for pagination, e.g., << < 1 2 3 > >>
//  paginatorRequestor is a method that requests a paginator from the server
OLD.getPaginateNavigator = function (paginator, paginatorRequestor, objectName) {

    // Items Per Page Selector -- user chooses how many items to display per page
    var itemsPerPageSelector = OLD.getItemsPerPageSelector(paginator,
                                                paginatorRequestor, objectName);

    return $('<div>').addClass('old-pagin-nav')
        // First Page
        .append($('<button>').text('first').addClass('float-left')
            .click(function () {paginatorRequestor({page: paginator.first_page});})
            .attr({'disabled': (paginator.first_page === paginator.page),
                  'title': 'first page', 'data-shortcut': 'ctrl+lArrow'})
            .button({icons: {primary: 'ui-icon-seek-first'}, text: false}))
        // Previous Page
        .append($('<button>').text('prev').addClass('float-left')
            .click(function () {paginatorRequestor({page: paginator.previous_page});})
            .attr({'disabled': !paginator.previous_page,
                  'title': 'previous page', 'data-shortcut': 'lArrow'})
            .button({icons: {primary: 'ui-icon-seek-prev'}, text: false}))
        // Items Per Page Selector
        .append(itemsPerPageSelector)
        // 3 Pages Back
        .append($('<button>').text(paginator.page - 3)
            .attr('title', 'page ' + (paginator.page - 3) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 3});})
            .button().toggle((paginator.page - 3 > 0)))
        // 2 Pages Back
        .append($('<button>').text(paginator.page - 2)
            .attr('title', 'page ' + (paginator.page - 2) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 2});})
            .button().toggle((paginator.page - 2 > 0)))
        // 1 Page Back
        .append($('<button>').text(paginator.page - 1)
            .attr('title', 'page ' + (paginator.page - 1) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 1});})
            .button().toggle((paginator.page - 1 > 0)))
        // Current Page (always disabled, displays page count)
        .append($('<button>').text(paginator.page + '/' + paginator.page_count)
            .attr('disabled', true).button())
        // 1 Page Forward
        .append($('<button>').text(paginator.page + 1)
            .attr('title', 'page ' + (paginator.page + 1) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 1});})
            .button().toggle((paginator.page +1 <= paginator.page_count)))
        // 2 Pages Forward
        .append($('<button>').text(paginator.page + 2)
            .attr('title', 'page ' + (paginator.page +2) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 2});})
            .button().toggle((paginator.page + 2 <= paginator.page_count)))
        // 3 Pages Forward
        .append($('<button>').text(paginator.page + 3)
            .attr('title', 'page ' + (paginator.page + 3) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 3});})
            .button().toggle((paginator.page + 3 <= paginator.page_count)))
        // Last Page
        .append($('<button>').text('end').addClass('float-right')
            .click(function () {paginatorRequestor({page: paginator.last_page});})
            .attr({disabled: (paginator.last_page === paginator.page),
                  title: 'last page', 'data-shortcut': 'ctrl+rArrow'})
            .button({icons: {primary: 'ui-icon-seek-end'}, text: false}))
        // Next Page
        .append($('<button>').text('next').addClass('float-right')
            .click(function () {paginatorRequestor({page: paginator.next_page});})
            .attr({'disabled': !paginator.next_page, 'title': 'next page',
                  'data-shortcut': 'rArrow'})
            .button({icons: {primary: 'ui-icon-seek-next'}, text: false}))
        // Disable all buttons after one is clicked (prevent double submit)
        .find('button').click(function () {$(this).attr('disabled', true);}).end();
}



// Get Page -- return the #old-page div and do some cleanup
OLD.getPage = function () {
    // Remove any explanation divs that may be floating around
    $('.old-explanation').remove();

    // Close any login dialog boxes
    OLD.closeLoginDialogBox();

    // Remove previous formTabbing handlers
    $(document).unbind('.formTabbing');

    return $('#old-page');
}

// Get Page Header -- return the header div for an OLD page
OLD.getPageHeader = function (html) {
    return $('<div>')
                .html($('<div>').addClass('old-widget-header-text').text(html))
                .addClass('old-widget-header ui-widget-header ui-corner-top');
}

// Get Page Body -- return the body div for an OLD Page
OLD.getPageBody = function (html) {
    return $('<div>').html(html).addClass('old-widget-body')
}


////////////////////////////////////////////////////////////////////////////////
// OLD.forms
////////////////////////////////////////////////////////////////////////////////



// Display Validation Errors (exclamation mark icons)
OLD.displayValidationErrors = function (errors, context) {

    // Remove any explanation widgets
    $('.old-explanation').remove();

    // Reset the border colors
    $('select, input, textarea', context)
        .css('border-color', OLD.jQueryUIColors.defBo);

    // Put an error border on each invalid input & display the validation
    //  error widget
    var fields = [];
    for (var error in errors) {
        var field = $($('.' + error, context).get(0));
        fields.push(field);
        field.css('border-color', OLD.jQueryUIColors.errBo);
        $('li:has(.' + error + ')', context)
            .append(OLD.validationErrorWidget(errors[error]));
    }

    // Focus and scroll to the topmost invalid field
    fields[0].focus();
    $('body').animate({scrollTop: fields[0].offset().top - 30}, 'normal');
}


// OLD Date Object -- a simple date object that is adamantly naive about time
//  zones, DST, UTC, etc.  Input is an ISO 8601 date string, e.g., 2012-04-21
OLD.Date = function (ISODateString) {
    var datePatt = /^\d{4}-\d{2}-\d{2}$/;
    if (datePatt.test(ISODateString)) {
        ISODateArray = ISODateString.split('-');
        this.year = ISODateArray[0];
        this.month = ISODateArray[1];
        this.date = ISODateArray[2];
        this.monthString = {'01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
            '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug', '09': 'Sep',
            '10': 'Oct', '11': 'Nov', '12': 'Dec'}[this.month];
        this.humanReadable = this.monthString + ' ' + this.date + ', ' + this.year;
        this.getHumanReadable = function () {
            return this.humanReadable;
        }
    }
}

// Extend the JavaScript Date object to parse UTC strings AS UTC dates
// Assumes the format "2012-04-23T18:47:02.734181" for ISODateTimeString
Date.prototype.parseAsUTC = function (ISODateTimeString) {
    var ISODateTimeArray = ISODateTimeString.split(/[\-T:\.]/);
    this.setUTCFullYear(ISODateTimeArray[0]);
    this.setUTCMonth(parseInt(ISODateTimeArray[1]) - 1, 10);
    this.setUTCDate(ISODateTimeArray[2]);
    this.setUTCHours(ISODateTimeArray[3]);
    this.setUTCMinutes(ISODateTimeArray[4]);
    this.setUTCSeconds(ISODateTimeArray[5]);
    if (ISODateTimeArray[6] !== undefined)
        this.setUTCMilliseconds(ISODateTimeArray[6].slice(0, 3) + '.' +
                                ISODateTimeArray[6].slice(3));
    return this;
}

// Pretty Date -- Some minor modifications of John Resig's script:
//  notably, this requires the parseAsUTC extension to the Date object as
//  defined above.
/*
 * JavaScript Pretty Date
 * Copyright (c) 2011 John Resig (ejohn.org)
 * Licensed under the MIT and GPL licenses.
 */

// Takes an ISO time and returns a string representing how
// long ago the date represents.
OLD.prettyDate = function (time) {
    var date = new Date().parseAsUTC(time);
    var now = new Date();

    // diff in seconds (getTime returns milliseconds, so divide by 1000)
    var diff = ((now.getTime() - date.getTime()) / 1000);

    // diff in days (86,400 in a day (60 x 60 x 24))
    var day_diff = Math.floor(diff / 86400);

    if (isNaN(day_diff) || day_diff < 0)
        return;

    return day_diff == 0 && (
            diff < 60 && "just now" ||
            diff < 120 && "1 minute ago" ||
            diff < 3600 && Math.floor(diff / 60) + " minutes ago" ||
            diff < 7200 && "1 hour ago" ||
            diff < 86400 && Math.floor(diff / 3600) + " hours ago") ||
        day_diff == 1 && "Yesterday" ||
        day_diff < 7 && day_diff + " days ago" ||
        day_diff == 7 && "1 week ago" ||
        day_diff < 31 && Math.ceil( day_diff / 7 ) + " weeks ago" ||
        day_diff >= 31 && date.toString();
}



// Form -- prototype for Form objects.
//  Initialization entails taking the attributes of a dict-like form object
//  received as JSON from the server-side code.
OLD.forms.Form = function (formObject) {
    // Initialization: take the properties of the formObject supplied by the
    //  server-side code as a JSON object

    // Assimilate JSONFormObject's properties
    this.JSONFormObject = formObject;
    for (var key in formObject) {
        this[key] = formObject[key];
    }

    // Show Additional Form Data (secondary/metadata & buttons)
    this.showAdditionalFormData = function (jQFormDOMObject) {
        jQFormDOMObject
            .animate({'border-color': OLD.jQueryUIColors.defBo}, 'slow');
        $('.old-form-buttons, .old-form-secondary-data, ' +
          '.old-form-hide-button', jQFormDOMObject).slideDown('slow');
    }

    // Hide Additional Form Data (secondary/metadata & buttons)
    this.hideAdditionalFormData = function (jQFormDOMObject) {
        jQFormDOMObject.css({'border-color': 'transparent'});
        $('.old-form-buttons, .old-form-secondary-data, ' +
          '.old-form-hide-button', jQFormDOMObject).slideUp('slow');
    }

    // Toggle Additional Form Data (secondary/metadata & buttons)
    this.toggleAdditionalFormData = function (jQFormDOMObject) {
        var hidden = (jQFormDOMObject.find('.old-form-buttons')
                      .css('display') === 'none');
        if (hidden)
            this.showAdditionalFormData(jQFormDOMObject);
        else
            this.hideAdditionalFormData(jQFormDOMObject);
    }

    // Highlight Form -- give the inputted jQFormDOMObject the ui-state-highlight
    //  class, remove that class from all others and change the
    //  indexOfHighlightedForm property of $('body').
    this.highlightForm = function(jQFormDOMObject) {
        $('.old-form-object').removeClass('ui-state-highlight');
        jQFormDOMObject.addClass('ui-state-highlight');
        var index = jQFormDOMObject.closest('table.old-pagin-item').data('index');
        $('body').data('indexOfHighlightedForm', index);
    }

    // Return an HTML representation of the Form
    this.html = function () {

        var form = this;

        // Phonetic Transcription Div
        var phoneticTranscriptionDiv = (this.phoneticTranscription !== null &&
                                        this.phoneticTranscription !== "") ?
            ($('<div>').addClass('old-form-phoneticTranscription')
                .text(this.phoneticTranscription)) : '';

        // Transcription Div
        var transcriptionDiv = (this.transcription !== "") ?
            ($('<div>').addClass('old-form-transcription')
                .text(this.grammaticality + this.transcription)) : '';

        // Morpheme Break Div
        var morphemeBreakDiv = (this.morphemeBreak !== "") ?
            ($('<div>').addClass('old-form-morphemeBreak')
                    .text(this.morphemeBreak)) : '';

        // Morpheme Gloss Div
        var morphemeGlossDiv = (this.morphemeGloss !== "") ?
            ($('<div>').addClass('old-form-morphemeGloss')
                .text(this.morphemeGloss)) : '';

        // Glosses Div
        var glossesDiv = $('<div>').addClass('old-form-glosses');
        $.each(this.glosses, function () {
            glossesDiv.append($('<div>').addClass('old-form-gloss')
                .append($('<span>').addClass('old-form-gloss-gram')
                    .text(this.glossGrammaticality))
                .append($('<span>').addClass('old-form-gloss-gloss')
                    .text(this.gloss)));
        });

        // id Div
        var idDiv = $('<div>').addClass('old-form-id')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('id'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.id));

        // Comments Div
        var commentsDiv = (this.comments !== "") ? 
            ($('<div>').addClass('old-form-comments')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('comments'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.comments))) : "";

        // Speaker Comments Div
        var speakerCommentsDiv = (this.speakerComments !== "") ? 
            ($('<div>').addClass('old-form-speakerComments')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('speaker comments'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.speakerComments))) : '';

        // Elicitation Method Div
        var elicitationMethodDiv = (this.elicitationMethod !== null) ?
            ($('<div>').addClass('old-form-elicitationMethod')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('elicitation method'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.elicitationMethod.name))) : '';

        // Keywords Div
        if (this.keywords.length !== 0) {
            var keywordsDiv = $('<div>').addClass('old-form-keywords')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('keywords'));
            var keywordsContent = $('<div>')
                .addClass('old-form-secondary-data-content');
            $.each(this.keywords, function () {
                keywordsContent.append($('<div>').addClass('old-form-keyword')
                    .text(this.name));
            });
            keywordsDiv.append(keywordsContent);
        } else {
            keywordsDiv = "";
        }

        // Syntactic Category String Div
        var syntacticCategoryStringDiv = (
                this.syntacticCategoryString !== null &&
                this.syntacticCategoryString !== "") ?
            ($('<div>').addClass('old-form-syntacticCategoryString')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('syntactic category string'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.syntacticCategoryString))) : '';

        // Syntactic Category Div
        var syntacticCategoryDiv = (this.syntacticCategory !== null) ?
            ($('<div>').addClass('old-form-syntacticCategory')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('syntactic category'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.syntacticCategory.name))) : '';

        // Speaker Div
        var speakerDiv = (this.speaker !== null) ?
            ($('<div>').addClass('old-form-speaker')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('speaker'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.speaker.firstName + ' ' +
                          this.speaker.lastName))) : '';

        // Elicitor Div
        var elicitorDiv = (this.elicitor !== null) ?
            ($('<div>').addClass('old-form-elicitor')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('elicitor'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.elicitor.firstName + ' ' +
                          this.elicitor.lastName))) : '';

        // Verifier Div
        var verifierDiv = (this.verifier !== null) ?
            ($('<div>').addClass('old-form-verifier')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('verifier'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.verifier.firstName + ' ' +
                          this.verifier.lastName))) : '';

        // Source Div
        var sourceDiv = (this.source !== null) ?
            ($('<div>').addClass('old-form-source')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('source'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(this.source.authorFirstName + ', ' +
                          this.source.authorLastName + ' (' +
                          this.source.year + ')'))) : '';

        // Date Elicited Div
        var dateElicitedDiv = (this.dateElicited !== null) ?
            ($('<div>').addClass('old-form-dateElicited')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('elicited'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text((new OLD.Date(this.dateElicited).getHumanReadable()))))
            : '';

        // Datetime Entered Div
        var datetimeEnteredDiv = (this.datetimeEntered !== null) ?
            ($('<div>').addClass('old-form-datetimeEntered')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('entered'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(OLD.prettyDate(this.datetimeEntered)))) : '';

        // Datetime Modified Div
        var datetimeModifiedDiv = $('<div>').addClass('old-form-datetimeModified')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('last modified'))
                .append($('<div>').addClass('old-form-secondary-data-content')
                    .text(OLD.prettyDate(this.datetimeModified)));

        // Files Div -- right now this just displays a list of file names
        if (this.files.length !== 0) {
            var filesDiv = $('<div>').addClass('old-form-files')
                .append($('<div>').addClass('old-form-secondary-data-label')
                    .text('files'));
            var filesContent = $('<div>')
                .addClass('old-form-secondary-data-content');
            $.each(this.files, function () {
                filesContent.append($('<div>').addClass('old-form-file')
                    .text(this.name));
            });
            filesDiv.append(filesContent);
        } else {
            filesDiv = "";
        }

        // IGT Div
        var igtDiv = $('<div>').addClass('old-form-igt')
            .append(phoneticTranscriptionDiv)
            .append(transcriptionDiv)
            .append(morphemeBreakDiv)
            .append(morphemeGlossDiv);

        // Primary Data Div (IGT Div + glosses)
        var primaryDataDiv = $('<div>').addClass('old-form-primary-data')
            .append(igtDiv)
            .append(glossesDiv);

        // Secondary Data Div (everything but primary)
        var secondaryDataDiv = $('<div>').addClass('old-form-secondary-data')
            .append(idDiv)
            .append(commentsDiv)
            .append(speakerCommentsDiv)
            .append(elicitationMethodDiv)
            .append(keywordsDiv)
            .append(syntacticCategoryDiv)
            .append(syntacticCategoryStringDiv)
            .append(speakerDiv)
            .append(elicitorDiv)
            .append(verifierDiv)
            .append(sourceDiv)
            .append(dateElicitedDiv)
            .append(datetimeEnteredDiv)
            .append(datetimeModifiedDiv)
            .append(filesDiv);

        // Buttons Div
        var buttonsDiv = $('<div>').addClass('old-form-buttons')
            .append($('<button>').text('Update'))
            .append($('<button>').text('Associate'))
            .append($('<button>').text('Export'))
            .append($('<button>').text('Remember'))
            .append($('<button>').text('Delete'))
            .append($('<button>').text('Duplicate'))
            .append($('<button>').text('History'))
            .buttonset()

        // Hide Button Div
        var hideButton = $('<button>').text('hide').addClass('float-right')
                .addClass('old-form-hide-button')
                .click(function (event) {
                    event.stopPropagation();
                    var jQFormDOMObject = $(this).closest('.old-form-object');
                    form.hideAdditionalFormData(jQFormDOMObject);
                })
                .button({icons: {primary: 'ui-icon-close'}, text: false});

        // Form Div
        var formDiv = $('<div>').addClass('old-form-object ui-corner-all')
            .data('id', this.id)    // Store the id of this form
            .append(hideButton.hide())
            .append(buttonsDiv.hide())
            .append(primaryDataDiv)
            .append(secondaryDataDiv.hide())
            .click(function () {
                form.showAdditionalFormData($(this));
                form.highlightForm($(this));
            });

        return formDiv;
    }
}



// Browse Forms
OLD.forms.browse = function (options) {
    OLD.showSpinner(); // Tell the user something is happening

    // Tell the paginator how many items_per_page we want
    options = options || {};
    options = $.extend(options, {items_per_page:
                    OLD.userSettings.formItemsPerPage});

    // Asynchronous GET request
    $.get('form/browse_ajax', options, OLD.forms.handlePaginatorResponse, 'json');
}

// Handle Form Paginator Response
OLD.forms.handlePaginatorResponse = function (response, statusText) {

    if (statusText === "success") {
        if (response === "unauthenticated") {
            OLD.openLoginDialogBox();
        } else if (response === "unauthorized") {
            console.log('Show them the unauthorized warning');
        } else {
            OLD.forms.displayForms(response);
        }
    } else {
        alert('Failed to retrieve Forms for browsing.');
    }

    // Response has been handled so hide the spinner
    OLD.hideSpinner();
}

// Create Login Dialog Box
OLD.createLoginDialogBox = function () {
    // Create the .old-login-dialog div to dialogify; assign input border color;
    //  create hidden .old-login-failed span
    $('<div>').hide().addClass('old-login-dialog')
        .html($('div.template.loginForm').children().clone())
        .find('input').css("border-color", OLD.jQueryUIColors.defBo).end()
        .append($('<span>').hide()
            .addClass('ui-state-error ui-corner-all old-login-failed'))
        .appendTo('body')
        .dialog({buttons: {
                    'Forgot password' : function () {
                        OLD.openForgotPasswordDialogBox();
                    },
                    Cancel: function () {
                        $('.ui-dialog-titlebar-close').click();
                    },
                    Login: function () {
                        $('.old-login-dialog-widget form.loginLogin').submit();
                    }
                },
                dialogClass: 'old-login-dialog-widget',
                title: 'Login',
                width: 400,
                open: function () {
                    $('.old-login-dialog-widget button').each(function () {
                        $(this).attr('tabindex', 1)});
                },
                beforeClose: function () {
                    OLD.cleanUpLoginDialogBox({clearFields: true,
                                              removeFocus: true});
                },
                autoOpen: false
        });

    // Render the "Login" button with the active display signifying to the user
    //  that the Return key submits the login form
    var loginButton = $($('.old-login-dialog-widget button').get(-1));
    loginButton.addClass('ui-state-active');

    // Handle the response from the login/authenticate_ajax controller action
    function handleResponse(responseJSON) {
        OLD.hideSpinner();
        if (responseJSON.valid) {
            if (responseJSON.authenticated) {
                console.log('valid and authentic');
            } else {
                OLD.cleanUpLoginDialogBox();
                // Tell the user that their credentials were incorrect
                $('.old-login-dialog-widget span.old-login-failed').show()
                    .text('The username or password you entered is incorrect.');
            }
        } else {
            OLD.cleanUpLoginDialogBox();
            // Display the invalid field inputs
            OLD.displayValidationErrors(responseJSON.errors,
                                              $('.old-login-dialog-widget'));
        }
    }

    // Handle an error in the server response
    function handleError(jqXHR, exception){
        OLD.hideSpinner();
        alert('Response error: ' + jqXHR.status + ' | ' + exception);
    }

    // Define the Login form's submit action
    $('.old-login-dialog-widget form.loginLogin').submit(function (event) {
        // Let the user know something is happening
        OLD.showSpinner();

        // Remove any validation error icons and explain widgets
        $('.old-val-err-widget, .old-explanation').remove();

        // Disable the Login button
        loginButton.attr('disabled', 'disabled');

        // Make the Ajax call
        $(this).ajaxSubmit({success: handleResponse,
                            dataType: 'json',
                            error: handleError});
        return false;
    });

}

// Open Login Dialog Box
OLD.openLoginDialogBox = function () {
    $('body .old-login-dialog').dialog('open');

    // Bind the Enter key to the "Login" button of the login dialog box
    $('.old-login-dialog-widget input')
        .bind('keydown.loginWithEnter', function (event) {
            if (event.which === 13) {
                event.stopImmediatePropagation();
                event.stopPropagation();
                $('.old-login-dialog-widget button').get(-1).click();
            }
        });
}

// Clean Up Login Dialog Box -- remove validation error widgets, unbind shortcuts
OLD.cleanUpLoginDialogBox = function (options) {

    var o = options || {};

    // Clear the input fields, if requested
    if (o.clearFields === true) $('.old-login-dialog-widget input').val('');

    // Remove focus, if requested
    if (o.removeFocus === true) $('.old-login-dialog-widget input').blur();

    // Re-enable the Login button and give it ui-state-active
    $($('.old-login-dialog-widget button').get(-1)).attr('disabled', false)
        .addClass('ui-state-active');

    // Remove any validation error icons and explain widgets
    $('.old-val-err-widget, .old-explanation').remove();

    // Remove any invalid credentials notifications
    $('.old-login-dialog-widget span.old-login-failed').text('').hide();

    // Restore the default border color of the input fields
    $('.old-login-dialog-widget input')
        .css("border-color", OLD.jQueryUIColors.defBo);
}

// Close the Login Dialog Box (there should only ever be one in existence)
OLD.closeLoginDialogBox = function () {
    $('.ui-dialog-titlebar-close').click();
}

// CACHEING FORMS -- Using localStorage to start
// 1. in options to browse_ajax request have a boolean 'ids_only' parameter
// 2. ids_only = true: server returns [(id, datetimeModified), etc.]
// 3. client displays Forms from localStorage with matching ids
// 4. client requests Forms that it doesn't have or that have been modified
// 5. server returns requested Forms
// 6. redundant server-client passing of Forms is reduced/eliminated.

// Display Form
OLD.forms.displayForm = function (formObject) {
    var form = new OLD.forms.Form(formObject);

    // Create Header & Body
    OLD.getPage().html($('<div>').addClass('old-forms-view-one-interface')
        .append(OLD.getPageHeader('View Form ' + form.id))
        .append(OLD.getPageBody()));

    var body = $('#old-page .old-widget-body');

    body.append(form.html());
}


// Check Authentication -- checks whether the user is authenticated
OLD.checkAuthentication = function () {
    $.get('login/check_authentication_ajax', null, registerAuthentication,
          'json');
    function registerAuthentication(responseJSON, statusText) {
        if (responseJSON) {
            console.log('We are logged in');
            OLD.logoutifyLoginButton();
        } else {
            console.log('We are not logged in');
            OLD.initializeLoginButton();
        }
    }
}

// Display Forms
//  Called by an Ajax request that returns a paginator
OLD.forms.displayForms = function (paginator) {

    // Create Header & Body
    var headerMsg = 'Browse (' + paginator.item_count + ' Forms, ' +
                        paginator.page_count + ' pages)';
    OLD.getPage().html($('<div>').addClass('old-forms-browse-interface')
        .append(OLD.getPageHeader(headerMsg))
        .append(OLD.getPageBody()));
    var header = $('#old-page .old-widget-header');
    var body = $('#old-page .old-widget-body');

    body.css('min-height', $(document).height() - 130)

    // Paginator Navigator -- append to header
    var paginateNavigator = OLD.getPaginateNavigator(paginator,
                                                OLD.forms.browse, 'form');
    header.append(paginateNavigator.clone(true));

    // Expand All Button -- reveal additional data in all Forms displayed
    var expandAllButton = $('<button>').text('Expand All')
        .attr('data-shortcut', 'alt+dArrow')
        .button({icons: {primary: 'ui-icon-circle-arrow-s'},
                text: false})
        .click(function () {
            $('.old-form-object').each(function () {
                (new OLD.forms.Form()).showAdditionalFormData($(this));
            });
        })

    // Collapse All Button -- hide additional data in all Forms displayed
    var collapseAllButton = $('<button>').text('Collapse All')
        .attr('data-shortcut', 'alt+uArrow')
        .button({icons: {primary: 'ui-icon-circle-arrow-n'},
                text: false})
        .click(function () {
            $('.old-form-object').each(function () {
                (new OLD.forms.Form()).hideAdditionalFormData($(this));
            });
        })

    // Forms Actions Div in header -- expand all, collapse all
    var formsActionsDiv = $('<div>').addClass('old-forms-actions')
            .append(expandAllButton)
            .append(collapseAllButton);
    header.append(formsActionsDiv);

    // Display each form in the current page (along with its index within
    //  the pagination, e.g., (1), (2), etc.)
    pageItems = $('<div>').addClass('old-pagin-items');
    $.each(paginator.items, function (index, item) {
        var form = new OLD.forms.Form(item);
        var paginIndex = index + parseInt(paginator.first_item);
        pageItems.append(
            $('<table>').addClass('old-pagin-item')
                .data('index', index)
                .append($('<tr>')
                    .append($('<td>').addClass('old-pagin-item-index')
                        .text('(' + paginIndex + ')'))
                    .append($('<td>').addClass('old-pagin-item-content')
                        .append(form.html()
                            .css({position: 'relative', top: '-11px'})
                            .hide().fadeIn('slow')))));
    });
    body.append(pageItems);

    // Correctly align the IGT data
    $('.old-form-igt').igt();

    // Paginator Navigator at bottom too
    body.append(paginateNavigator.clone(true).
        addClass('old-pagin-nav-bottom'));

    // UI-ify IPP selects
    $('select.old-pagin-ipp-select').selectmenu({width: 200}); 

    // Highlight the first Form and bind keyboard shortcuts to it
    $('body').data('indexOfHighlightedForm', 0);
    $($('.old-form-object')[0]).addClass('ui-state-highlight');
    OLD.forms.bindKeyboardShortcutsToHighlightedForm();

    // Form Tabbing -- Bind Tab and Shift+Tab keydown events to highlight
    //  the next and previous Form DOM Objects respectively
    $(document).unbind('.formTabbing')  // Remove previous formTabbing handlers
        .bind('keydown.formTabbing', function (event) {
            if (event.shiftKey && event.which === 9) {
                event.preventDefault();
                OLD.forms.highlightForm('prev');
            } else if (event.which === 9) {
                event.preventDefault();
                OLD.forms.highlightForm('next');
            }
        });

    // Bind the keyboard shortcuts specified in the data-shortcut attributes
    //  to the click events
    OLD.bindKeyboardShortcutToClick($('#old-page button[data-shortcut]'));

    // Scroll to the top of the page
    $('body').animate({scrollTop: 0}, 'slow');
}

// Highlight Form -- adds the ui-state-highlight class to the next or previous
//  old-form-object div as determined by the value of o, 'prev' or 'next'.
//  The index of the currently highlighted one is held in
//  $('body').data('indexOfHighlightedForm').
OLD.forms.highlightForm = function (o) {
    // Get all OLD Form DOM objects (FDO) and remove any highlights
    formDOMObjects = $('.old-form-object').removeClass('ui-state-highlight');

    // Get index of currently highlighted FDO
    var index = $('body').data('indexOfHighlightedForm');

    // Calculate index of to-be-highlighted FDO & save it in <body>
    var index = {'prev': (((index - 1) < 0) ? (formDOMObjects.length - 1) :
                          (index - 1)),
                 'next': (((index + 1) >= formDOMObjects.length) ? (0) :
                          (index + 1))}[o];
    $('body').data('indexOfHighlightedForm', index);

    // Highlight the FDO and scroll to it
    $(formDOMObjects.get(index)).addClass('ui-state-highlight');
    $('body').animate({
        scrollTop: $(formDOMObjects.get(index)).offset().top - 30}, 'normal');

    // Bind keyboard shortcuts to the currently highlighted Form DOM object
    OLD.forms.bindKeyboardShortcutsToHighlightedForm();
}


// Scroll to the currently highlighted Form DOM object
OLD.forms.scrollToHighlightedForm = function () {
    var index = $('body').data('indexOfHighlightedForm');
    $('body').animate({
        scrollTop: $($('.old-form-object').get(index)).offset().top - 30},
        'normal');
}

// Bind Keyboard Shortcuts to Highlighted Form -- depending on what Form is
//  currently highlighted, the RETURN and ctrl + U/E/R/D key combinations will
//  have different effects.
OLD.forms.bindKeyboardShortcutsToHighlightedForm = function () {
    function getHighlightedFormJQDOMObject() {
        return $($('.old-form-object')
                    .get($('body').data('indexOfHighlightedForm')));
    }
    $(document).unbind('.formShortcuts')  // Remove previous formShortcuts handlers
        .bind('keydown.formShortcuts', function (event) {
            if (event.ctrlKey) {
                // U: Update
                if (event.which === 85) {
                    event.preventDefault();
                    var formJQDOMObject = getHighlightedFormJQDOMObject();
                    console.log('You want to update Form ' +
                                formJQDOMObject.data('id'));
                }
                // E: Export
                else if (event.which === 69) {
                    event.preventDefault();
                    var formJQDOMObject = getHighlightedFormJQDOMObject();
                    console.log('You want to export Form ' +
                                formJQDOMObject.data('id'));
                }
                // R: Remember
                else if (event.which === 82) {
                    event.preventDefault();
                    var formJQDOMObject = getHighlightedFormJQDOMObject();
                    console.log('You want to remember Form ' +
                                formJQDOMObject.data('id'));
                }
                // D: Delete
                else if (event.which === 68) {
                    event.preventDefault();
                    var formJQDOMObject = getHighlightedFormJQDOMObject();
                    console.log('You want to delete Form ' +
                                formJQDOMObject.data('id'));
                }
            }
            // Return: Expand/Collapse
            else if (event.which === 13) {
                event.preventDefault();
                var formJQDOMObject = getHighlightedFormJQDOMObject();
                (new OLD.forms.Form()).toggleAdditionalFormData(formJQDOMObject);
            }

        });
}

////////////////////////////////////////////////////////////////////////////////
// Application Settings
////////////////////////////////////////////////////////////////////////////////

OLD.ApplicationSettings = function () {
    this.itemsPerPageOptions = [1, 5, 10, 20, 50, 100];
}

////////////////////////////////////////////////////////////////////////////////
// User Settings
////////////////////////////////////////////////////////////////////////////////

OLD.UserSettings = function () {
    this.formItemsPerPage = 10;
}


////////////////////////////////////////////////////////////////////////////////
// OLD Global Methods
////////////////////////////////////////////////////////////////////////////////


// Get Items Per Page Selector (for paginators)
//  Used to change how many items are displayed in a pagination display
//  paginator parameter holds crucial first_item and items_per_page data
//  paginatorRequestor is the method that requests a new page (e.g., browse)
//  objectName (e.g., 'form') is required to get the appropriate user setting
OLD.getItemsPerPageSelector = function (paginator, paginatorRequestor,
                                        objectName) {

    // Get relevant xItemsPerPage from userSettings, based on objectName
    var itemsPerPage = OLD.userSettings[objectName + 'ItemsPerPage'];

    // Build the select element
    function conjug(n) {return (n === 1) ? '' : 's';}
    var select = $('<select>').addClass('old-pagin-ipp-select');
    $.each(OLD.applicationSettings.itemsPerPageOptions, function (index, item) {
        select.append($('<option>')
            .text(item + ' item' + conjug(item) + ' per page')
            .attr({'value': this, 'selected': (item === itemsPerPage)}));
    });

    // Bind the select's change event to a request for a new page with the new
    //  items_per_page argument
    select.change(function () {
        OLD.userSettings[objectName + 'ItemsPerPage'] = parseInt($(this).val());
        paginatorRequestor({items_per_page: parseInt($(this).val())});
    })

    // Return the select wrapped in a centered div
    //return $('<div>').addClass('old-pagin-ipp').append(select);
    return select;
}

// Paginate Navigator: stylized interface for pagination, e.g., << < 1 2 3 > >>
//  paginatorRequestor is a method that requests a paginator from the server
OLD.getPaginateNavigator = function (paginator, paginatorRequestor, objectName) {

    // Items Per Page Selector -- user chooses how many items to display per page
    var itemsPerPageSelector = OLD.getItemsPerPageSelector(paginator,
                                                paginatorRequestor, objectName);

    return $('<div>').addClass('old-pagin-nav')
        // First Page
        .append($('<button>').text('first').addClass('float-left')
            .click(function () {paginatorRequestor({page: paginator.first_page});})
            .attr({'disabled': (paginator.first_page === paginator.page),
                  'title': 'first page', 'data-shortcut': 'ctrl+lArrow'})
            .button({icons: {primary: 'ui-icon-seek-first'}, text: false}))
        // Previous Page
        .append($('<button>').text('prev').addClass('float-left')
            .click(function () {paginatorRequestor({page: paginator.previous_page});})
            .attr({'disabled': !paginator.previous_page,
                  'title': 'previous page', 'data-shortcut': 'lArrow'})
            .button({icons: {primary: 'ui-icon-seek-prev'}, text: false}))
        // Items Per Page Selector
        .append(itemsPerPageSelector)
        // 3 Pages Back
        .append($('<button>').text(paginator.page - 3)
            .attr('title', 'page ' + (paginator.page - 3) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 3});})
            .button().toggle((paginator.page - 3 > 0)))
        // 2 Pages Back
        .append($('<button>').text(paginator.page - 2)
            .attr('title', 'page ' + (paginator.page - 2) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 2});})
            .button().toggle((paginator.page - 2 > 0)))
        // 1 Page Back
        .append($('<button>').text(paginator.page - 1)
            .attr('title', 'page ' + (paginator.page - 1) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page - 1});})
            .button().toggle((paginator.page - 1 > 0)))
        // Current Page (always disabled, displays page count)
        .append($('<button>').text(paginator.page + '/' + paginator.page_count)
            .attr('disabled', true).button())
        // 1 Page Forward
        .append($('<button>').text(paginator.page + 1)
            .attr('title', 'page ' + (paginator.page + 1) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 1});})
            .button().toggle((paginator.page +1 <= paginator.page_count)))
        // 2 Pages Forward
        .append($('<button>').text(paginator.page + 2)
            .attr('title', 'page ' + (paginator.page +2) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 2});})
            .button().toggle((paginator.page + 2 <= paginator.page_count)))
        // 3 Pages Forward
        .append($('<button>').text(paginator.page + 3)
            .attr('title', 'page ' + (paginator.page + 3) + ' of ' +
                  paginator.page_count)
            .click(function () {paginatorRequestor({page: paginator.page + 3});})
            .button().toggle((paginator.page + 3 <= paginator.page_count)))
        // Last Page
        .append($('<button>').text('end').addClass('float-right')
            .click(function () {paginatorRequestor({page: paginator.last_page});})
            .attr({disabled: (paginator.last_page === paginator.page),
                  title: 'last page', 'data-shortcut': 'ctrl+rArrow'})
            .button({icons: {primary: 'ui-icon-seek-end'}, text: false}))
        // Next Page
        .append($('<button>').text('next').addClass('float-right')
            .click(function () {paginatorRequestor({page: paginator.next_page});})
            .attr({'disabled': !paginator.next_page, 'title': 'next page',
                  'data-shortcut': 'rArrow'})
            .button({icons: {primary: 'ui-icon-seek-next'}, text: false}))
        // Disable all buttons after one is clicked (prevent double submit)
        .find('button').click(function () {$(this).attr('disabled', true);}).end();
}

// Return the validation error widget (it displays validation errors)
OLD.validationErrorWidget = function (errorMsg) {
    return $('<div>').addClass('ui-state-error ui-corner-all old-val-err-widget')
        .append($('<span>').addClass('ui-icon ui-icon-alert'))
        .mouseenter(function (event) {
            OLD.explain(errorMsg, 'error', event);
        });
}

// Explain -- display a pop-up message explaining something just below and to
//  the right of the mouse location (based on JQIA's termifier)
OLD.explain = function (msg, type, event) {
    var explainClass = (type === 'highlight') ? 'ui-state-highlight' :
        'ui-state-error';
    $('.old-explanation').remove();
    $('<div>')
        .addClass(explainClass + ' ui-corner-all old-explanation')
        .css({position: 'absolute', display: 'none',
             top: event.pageY + 5, left: event.pageX + 5})
        .click(function () {$(this).fadeOut('slow');})
        .appendTo('body')
        .append($('<div>').html(msg))
        .fadeIn('slow');
}

// Remove Explanations
OLD.removeExplanations = function () {
    $('.old-explanation').remove();
}

// Show Spinner Indicator (http://www.ajaxload.info/)
OLD.showSpinner = function () {
    $('body').append($('<img>')
        .attr({'src': 'images/ajax-loader.gif', 'id': 'spinner'}));
}

// Hide Spinner
OLD.hideSpinner = function () {$('#spinner').remove();}

// System Settings Page
OLD.systemSettings = function () {
    $('div#old-page-body')
        .html(
            $('<div>').addClass('heading').text('System Settings')
                .append($('div.template.systemSettings').children().clone()))
        .find('img.ui-theme-icon').click(function () {
            $('link[href*="jquery-ui-1.8.18.custom.css"]')
                .attr('rel', 'alternate');
            $('link.' + $(this).attr("data-theme"))
                .attr('rel', 'stylesheet');
        });
}

// Initialize Login Button -- set the icon to locked, bind it to open login box
OLD.initializeLoginButton = function () {
    // Button-ize it and make its border indiscernible
    //  Trying to emulate the jQuery UI dialog box close button, but I don't
    //  know how ...
    $('a.old-authenticated').text('Login')
        .button({icons: {primary: 'ui-icon-locked'}, text: false})
        .css('border-color', OLD.jQueryUIColors.defBa)
        .unbind('.loginButtonClick')
        .bind('click.loginButtonClick', function () {
            OLD.openLoginDialogBox();
        });
}

// Logoutify Login Button -- change the icon to unlocked, bind it to logout
OLD.logoutifyLoginButton = function () {
    $('a.old-authenticated').text('Logout')
        .button({icons: {primary: 'ui-icon-unlocked'}, text: false})
        .css('border-color', OLD.jQueryUIColors.defBa)
        .unbind('.loginButtonClick')
        .bind('click.loginButtonClick', function () {
            OLD.logout();
        });
}

// Logout -- logout of the OLD
OLD.logout = function () {
    console.log('You want to logout');
    $.get('login/logout_ajax', null, logoutInterface, 'json');

    // Change the interface to represent the logged out state
    function logoutInterface(responseJSON, statusText) {
        if (statusText === "success") {
            OLD.initializeLoginButton();
        } else {
            alert('Sorry, logout failed.');
        }
    }
}

////////////////////////////////////////////////////////////////////////////////
// Display Pages
////////////////////////////////////////////////////////////////////////////////

OLD.home = function () {
    if (OLD.pages.homePage === undefined) {
        OLD.pages.homePage = new OLD.Page({url: 'home/index_ajax',
                                          headerText: 'Home'});
    }
    OLD.pages.homePage.display();
}

////////////////////////////////////////////////////////////////////////////////
// On DOM loaded stuff
////////////////////////////////////////////////////////////////////////////////

$(function () {

    // Set the height of the page based on the window size (Firefox bug? ...)
    var windowHeight = $(window).height() - 57;
    $('#old-page').css({'min-height': windowHeight});

    // Get the jQuery UI Colors
    OLD.jQueryUIColors = $.getJQueryUIColors();

    // Application Settings object
    OLD.applicationSettings = new OLD.ApplicationSettings();

    // User Settings object
    OLD.userSettings = new OLD.UserSettings();

    // Create keyboard shortcuts from 'data-shortcut' attributes
    $('[data-shortcut][data-function]').each(function () {
        OLD.bindFunctionToKeyboardShortcut($(this).attr('data-function'),
                                           $(this).attr('data-shortcut'));
        $(this).append($('<span>').addClass('float-right')
            .text(OLD.getShortcutAbbreviation($(this).attr('data-shortcut'))));
    });

    // Create the SuperFish dropdown main menu (themed to match the jQuery UI)
    $('ul.sf-menu')
        .find('a').attr('tabindex', 2).end()
        .supersubs({minWidth: 12, maxWidth: 27, extraWidth: 2})
        .superfish({autoArrows: false})
        .superfishJQueryUIMatch(OLD.jQueryUIColors);
    $('div#old-main-menu').css(OLD.jQueryUIColors.def);

    // Bind clicks on the links of the main menu.  The data-template value of
    //  the anchor corresponds to the relevant template class.
    $('ul.sf-menu a[data-template]').click(function (event) {
        event.preventDefault();
        $('div#old-page-body')
            .html($('div.template.' + $(this).attr('data-template'))
                .children().clone());
    });

    // data-function attribute defines functions object, method pairs where the
    //  method is that to be run on the click event, e.g., OLD.object.method()
    $('ul.sf-menu a[data-function]').click(function (event) {
        event.preventDefault();
        OLD.getFunctionFromDataFunctionAttribute(
                                            $(this).attr('data-function'))();
    });

    // Initialize the Login Button (lock/unlock icon in main menu div)
    OLD.initializeLoginButton();

    // Tabindex of 1 to all input elements (necessary here?)
    $('textarea, select, input, button').attr({tabindex: "1"});

    // Create Login Dialog Box
    OLD.createLoginDialogBox();

    // Check if the user is logged in
    OLD.checkAuthentication();

    // Secondary Object Stores -- local caches of secondary OLD object data
    OLD.grammaticalities = new OLD.GrammaticalitiesStore();
    OLD.elicitationMethods = new OLD.ElicitationMethodsStore();
    OLD.keywords = new OLD.KeywordsStore();
    OLD.categories = new OLD.CategoriesStore();
    OLD.speakers = new OLD.SpeakersStore();
    OLD.users = new OLD.UsersStore();
    OLD.sources = new OLD.SourcesStore();


    // Display the home page
    OLD.home();
});


////////////////////////////////////////////////////////////////////////////////
// JQuery Extensions
////////////////////////////////////////////////////////////////////////////////

(function($) {

    // superfishJQueryUIMatch alters the superfish menu to match the jQuery UI
    //  theme currently in use
    $.fn.superfishJQueryUIMatch = function (colorsProvided) {
        // Get the jQuery UI theme's colors
        var colors = (typeof colorsProvided == "undefined") ?
            $.getJQueryUIColors() : colorsProvided

        // Alter the superfish styles to match the jQuery UI theme, etc.
        $(this)
            .find('li')
                .css(colors.def).find('a').css('color', colors.defCo).end()
                .bind({
                    'mousedown': function (e) {
                        $(this).css(colors.act)
                            .children('a').css('color', colors.actCo)
                            .children('span.sf-icon-triangle-1-e')
                                .css("background-image", colors.actArrowEImg);
                        e.stopPropagation();
                    },
                    'mouseup': function () {
                        $(this).css(colors.hov)
                            .children('a').css('color', colors.hovCo)
                            .children('span.sf-icon-triangle-1-e')
                                .css("background-image", colors.hovArrowEImg);
                    },
                    'mouseleave': function () {
                        $(this).css(colors.def)
                            .children('a').css('color', colors.defCo)
                            .children('span.sf-icon-triangle-1-e')
                                .css("background-image", colors.defArrowEImg);
                    },
                    'click': function () {$(this).hideSuperfishUl();}
                })
                .hover(function () {
                        $(this).css(colors.hov);
                        $(this).find('a').css('color', colors.hovCo);
                    }, function () {
                        $(this).css(colors.def);
                        $(this).find('a').css('color', colors.defCo);
                    }).end()
            .find('li.sfHover')
                .find('a').css('color', colors.hovCo).end().css(colors.hov).end()
            .find('li li:last-child')
                .addClass('ui-corner-bottom sf-option-bottom').end()
            .find('li li li:first-child')
                .addClass('ui-corner-tr sf-option-top').end()
            .find('li li:has(ul) > a')
                .append($('<span>').addClass("sf-icon-triangle-1-e")
                        .css("background-image", colors.defArrowEImg))
    }

    // Get the jQuery UI theme's colors (and east single triangle bg image)
    $.getJQueryUIColors = function () {
        $('body').append(
            $('<div>').addClass('jQueryUIColors')
                .append($('<button>').addClass('ui-state-default').text('b')
                    .button({icons: {primary: 'ui-icon-triangle-1-e'}}))
                .append($('<button>').addClass('ui-state-hover').text('b')
                    .button({icons: {primary: 'ui-icon-triangle-1-e'}}))
                .append($('<button>').addClass('ui-state-active').text('b')
                    .button({icons: {primary: 'ui-icon-triangle-1-e'}}))
                .append($('<button>').addClass('ui-state-error').text('b')
                    .button({icons: {primary: 'ui-icon-triangle-1-e'}}))
            );
        var defWS = $("div.jQueryUIColors button.ui-state-default");
        var hovWS = $("div.jQueryUIColors button.ui-state-hover");
        var actWS = $("div.jQueryUIColors button.ui-state-active");
        var errWS = $("div.jQueryUIColors button.ui-state-error");
        var colors = {
            defCo: defWS.css("color"),
            defBa: defWS.css("backgroundColor"),
            defBo: defWS.css("border-top-color"),
            defArrowEImg: defWS.find('span.ui-icon').css("background-image"),
            hovCo: hovWS.css("color"),
            hovBa: hovWS.css("backgroundColor"),
            hovBo: hovWS.css("border-top-color"),
            hovArrowEImg: hovWS.find('span.ui-icon').css("background-image"),
            actCo: actWS.css("color"),
            actBa: actWS.css("backgroundColor"),
            actBo: actWS.css("border-top-color"),
            actArrowEImg: actWS.find('span.ui-icon').css("background-image"),
            errCo: errWS.css("color"),
            errBa: errWS.css("backgroundColor"),
            errBo: errWS.css("border-top-color"),
            errArrowEImg: errWS.find('span.ui-icon').css("background-image")
        };
        colors.defBos = {'border-right-color': colors.defBo,
                         'border-left-color': colors.defBo,
                         'border-top-color': colors.defBo,
                         'border-bottom-color': colors.defBo};
        colors.hovBos = {'border-right-color': colors.hovBo,
                         'border-left-color': colors.hovBo,
                         'border-top-color': colors.hovBo,
                         'border-bottom-color': colors.hovBo};
        colors.actBos = {'border-right-color': colors.actBo,
                         'border-left-color': colors.actBo,
                         'border-top-color': colors.actBo,
                         'border-bottom-color': colors.actBo};
        colors.errBos = {'border-right-color': colors.errBo,
                         'border-left-color': colors.errBo,
                         'border-top-color': colors.errBo,
                         'border-bottom-color': colors.errBo};
        colors.def = $.extend({backgroundColor: colors.defBa,
                              color: colors.defCo}, colors.defBos);
        colors.hov = $.extend({backgroundColor: colors.hovBa,
                              color: colors.hovCo}, colors.hovBos);
        colors.act = $.extend({backgroundColor: colors.actBa,
                              color: colors.actCo}, colors.actBos);
        colors.err = $.extend({backgroundColor: colors.errBa,
                              color: colors.errCo}, colors.errBos);
        $('div.jQueryUIColors').remove();
        return colors;
    };

    // IGT - Interlinear Gloss Text -- this wrapped set method correctly aligns
    //  words in interlinear gloss text format into columns.  Each element of
    //  the set is expected to contain two or more elements and the text of
    //  each of these sub-elements is considered to be the line.  In the
    //  following example, 'les chiens', 'le-s chien-s' and 'DET-PL dog-PL' are
    //  the lines:
    //
    //    <div class="align-me">
    //      <div>les chiens</div>
    //      <div>le-s chien-s</div>
    //      <div>DET-PL dog-PL</div>
    //    </div>
    //
    //  Basic usage:
    //
    //    $('div.align-me').igt();
    //
    //  Usage with options:
    //
    //    $('div.align-me').igt({buffer: 20, lineGroupBuffer: 5, indent: 60,
    //                          minLineWidthAsPerc: 75});

    $.fn.igt = function (options) {

        // Align words in each element of the wrapped set
        $(this).each(function () {

            var container = $(this);

            // Each child is a line whose words may need alignment
            var children = $(this).children();

            // spanWidths holds the width of each span in each line; it will
            //  look something like [[49, 32, 40], [66, 49, 40], [61, 99, 25]]
            var spanWidths = [];  

            // colWidths holds the width of each column, i.e., the width of the
            //  longest <span>-wrapped word with index x, e.g., [66, 99, 40]
            var colWidths = [];

            // lineHeights holds height of each line
            var lineHeights = []; 


            ////////////////////////////////////////////////////////////////////
            // OPTIONS //
            ////////////////////////////////////////////////////////////////////

            if (options === undefined) options = {};

            // Number of pixels to put between each span
            var buffer = (options.buffer === undefined) ? 30: options.buffer;

            // Number of pixels to put between groups of lines ("lineGroups")
            var lineGroupBuffer = (options.lineGroupBuffer === undefined) ?
                                    10 : options.lineGroupBuffer;

            // Number of pixels to indent each subsequent line
            var indent = (options.indent === undefined) ? 40 : options.indent;

            // Minimum width of a line as a percentage of the container's width
            var minLineWidthAsPerc = (options.minLineWidthAsPerc === undefined) ?
                                    50 : options.minLineWidthAsPerc;

            // Line Group Class: class to give to line groups
            var lineGroupClass = (options.lineGroupClass === undefined) ?
                            'old-form-igt-line-group': options.lineGroupClass;

            ////////////////////////////////////////////////////////////////////
            // FUNCTIONS //
            ////////////////////////////////////////////////////////////////////

            // Spanify -- input: line of text; output: line with each word
            //  enclosed in a span tag
            function spanify(elementText) {
                return $.map(elementText.replace(/\s\s+/g, ' ').split(' '),
                    function (word) {
                        return '<span style="white-space: nowrap;">' + word +
                        '</span>';
                    }
                ).join(' ');
            }

            // Get Greatest Width -- return the greatest width among the words
            //  in the same 'column'.
            function getGreatestWidth(widths, index, spanIndex) {
                if (colWidths[spanIndex] === undefined) {

                    // E.g., from [[49, 32, 40], [66, 49], [61, 99, 25]],
                    //  return [40, 25] (assuming spanIndex = 2)
                    widths = $.map(widths, function (widthSet) {
                        if (widthSet.length == widths[index].length)
                            return widthSet[spanIndex];
                        else
                            return 0;
                    });

                    result = Math.max.apply(Math, widths); // Get the widest
                    colWidths[spanIndex] = result;  // Remember for later
                    return result;

                } else {
                    // We know max width of this column from previous iterations
                    return colWidths[spanIndex];
                }
            }

            // Set Width -- set the width of the span to the width of the widest
            //  span in the same column PLUS the buffer.
            function setWidth(index, spanIndex, span) {
                greatestWidth = getGreatestWidth(spanWidths, index, spanIndex);
                $(span).css({display: 'inline-block',
                            width: greatestWidth + buffer});
            }

            // Sum -- sum all integers in an array (c'mon Javascript!)
            function sum(array) {
                result = 0;
                for (i = 0;i < array.length;i += 1)
                    result += array[i];
                return result;
            }

            // Get New Max Width: get the max width of a "line group" based on
            //  the current max width, indent and minLineWidthAsPerc
            function getNewMaxWidth(currentMaxWidth, minLineWidth) {
                if ((currentMaxWidth - indent) > minLineWidth) {
                    return currentMaxWidth - indent;
                } else {
                    // Sorry, we can't reduce the width any further
                    return currentMaxWidth;
                }
            }


            ////////////////////////////////////////////////////////////////////
            // ALIGN THE WORDS IN THE LINES ALREADY //
            ////////////////////////////////////////////////////////////////////

            // Clone the children and enclose each word of each child clone in
            //  span tags, record the width of each such span tag and the height
            //  of each line.
            children.each(function (index, child) {
                // wrap words in spans
                $(child).html(spanify($(child).text()));

                // record the width of each span
                var widths = [];
                $('span', child).each(function (index, span) {
                    widths.push($(span).width());
                });
                spanWidths.push(widths);

                // Record the height of each line
                lineHeights.push($($('span', child)[0]).height());

            });

            // linesToColumnify is an array of indices representing the lines
            //  whose span-wrapped words need to be aligned.  Such lines have
            //  a word count that is greater than one and equal to that of all
            //  subsequent lines.
            var linesToColumnify = [];
            $.each(spanWidths, function (index, line) {
                // isColumnable returns true if the last line has more than two
                //  words and all lines from this one on down have the same word
                //  count
                function isColumnable(index, line) {
                    if (spanWidths[spanWidths.length - 1].length < 2)
                        return false;
                    for (var i = index + 1; i < spanWidths.length; i++) {
                        if (spanWidths[i].length !== spanWidths[index].length)
                            return false;
                    }
                    return true;
                }
                if (isColumnable(index, line)) linesToColumnify.push(index);
            });
            if (linesToColumnify.length < 2) linesToColumnify = [];

            // Set the width of each span tag to the width of the longest span
            //  tag in the same 'column' plus the buffer
            children.each(function (index, child) {
                // Only alter the width of spans inside of columnable lines
                if (linesToColumnify.indexOf(index) !== -1) {
                    //$(child).text($(child).text().replace(/ /g, ''));
                    $('span', child).each(function (spanIndex, span) {
                        setWidth(index, spanIndex, span);
                    });
                }
            });

            // If the container's height is not equal to the sum of the line
            //  heights, we have lines wrapping and need to fix that by breaking
            //  the lines into multiple lines.
            var containerHeight = $(this).height();
            if (containerHeight !== sum(lineHeights)) {
                var containerWidth = $(this).width();
                var minLineWidth = Math.round(minLineWidthAsPerc / 100 *
                                                containerWidth);

                // Create the lineGroups list of objects; this tells us the max
                //  width of each line and, indirectly via the spanWidths object,
                //  the slice of <span>-wrapped words we want in each line.
                var lineGroups = [{maxWidth: containerWidth, indent: 0,
                                 spanWidths: []}];
                $.each(colWidths, function (index, width) {
                    lineGroup = lineGroups[lineGroups.length - 1];
                    if ((sum(lineGroup.spanWidths) + width + buffer)
                        < lineGroup.maxWidth) {
                        lineGroup.spanWidths.push(width + buffer);
                    } else {
                        
                        lineGroups.push({maxWidth:
                            getNewMaxWidth(lineGroup.maxWidth, minLineWidth),
                            spanWidths: [width + buffer]});
                    }
                });

                // Create a new container that has the lines broken up,
                //  grouped and indented appropriately.
                var newContainer = $('<div>');
                var begin = 0;
                previousIndent = 0;
                $.each(lineGroups, function (index, lineGroup) {
                    var topMarg = (index !== 0) ? lineGroupBuffer : 'auto';
                    var currentIndent = ((lineGroup.maxWidth -
                        (index * indent)) < minLineWidth) ? previousIndent :
                        (index * indent);
                    previousIndent = currentIndent;

                    var lineGroupDiv = $('<div>')
                                            .addClass(lineGroupClass)
                                            .css({'margin-left': currentIndent,
                                                'margin-top': topMarg});
                    var end = begin + lineGroup.spanWidths.length;
                    container.children().clone(true).each(
                        function (index, line) {
                            lineGroupDiv.append(
                                $(line)
                                    .html($(line).children().slice(begin, end)));
                        }
                    );
                    newContainer.append(lineGroupDiv);
                    begin = end;
                });

                // Replace the container's children with those of the new container
                container.html(newContainer.children());
            }
        });
    }

})(jQuery);