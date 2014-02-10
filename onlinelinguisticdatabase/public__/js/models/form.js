var OLD = OLD || {};

(function() {
	'use strict';

	// Form Model
	// ----------

	// Our basic **Form** model has
	OLD.Form = Backbone.Model.extend({

		initialize: function () {
			this.on('change:transcription', function () {
				var transcription = this.get('transcription');
				console.log('transcription has been changed to ' + transcription);
			});
		},

		// Default attributes for the form
		// and ensure that each form created has `transcription` and `glosses`
        //  keys.
		defaults: {
			transcription: '',
			glosses: ['']
		}

	});

}());


/*
id INT PRIMARY KEY
transcription VARCHAR(255) NOT NULL
phoneticTranscription VARCHAR(255)
narrowPhoneticTranscription VARCHAR(255)
morphemeBreak VARCHAR(255)
morphemeGloss VARCHAR(255)
comments TEXT
speakerComments TEXT
grammaticality VARCHAR(255)

dateElicited DATE
datetimeEntered DATETIME
datetimeModified DATETIME DEFAULT NOW

syntacticCategoryString VARCHAR(255)
morphemeBreakIDs VARCHAR(1023)
morphemeGlossIDs VARCHAR(1023)
breakGlossCategory VARCHAR(1023)

elicitor_id INT (FOREIGN KEY user.id)
enterer_id INT (FOREIGN KEY user.id)
verifier_id INT (FOREIGN KEY user.id)
speaker_id INT (FOREIGN KEY speaker.id)
elicitationmethod_id INT (FOREIGN KEY elicitationmethod.id)
syntacticcategory_id INT (FOREIGN KEY syntacticcategory.id)
source_id INT (FOREIGN KEY source.id)

glosses (one-to-many)
keywords (many-to-many)
files (many-to-many)
*/