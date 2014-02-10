var OLD = OLD || {};
var ENTER_KEY = 13;

$(function() {

	// Kick things off by creating the **App**.
	//new app.AppView();
    var form = new OLD.Form({transcription: 'imitaa', glosses: ['dog', 'wolf']});
    form.set({transcription: 'imitaA'});
    
    $('#showform').click(function () {
        var formView = new OLD.FormView({model: form});
        formView.render();
    });

});
