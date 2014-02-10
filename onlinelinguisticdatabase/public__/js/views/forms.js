var OLD = OLD || {};

$(function() {
	'use strict';

	// Form Item View
	// --------------

	// The DOM element for a form item...
	OLD.FormView = Backbone.View.extend({

		//... is a div tag.
		tagName:  'div',
		//el: '#form1',

		// Cache the template function for a single item.
		template: _.template( $('#form-template').html() ),

		// The DOM events specific to an item.
		events: {
			'dblclick label':	'edit',
			'click .destroy':	'clear',
			'keypress .edit':	'updateOnEnter',
			'blur .edit':		'close'
		},
	
		// The FormView listens for changes to its model, re-rendering. Since
		// there's a one-to-one correspondence between a **Form** and a
		// **FormView** in this app, we set a direct reference on the model for
		// convenience.
		initialize: function() {
			this.model.on( 'change', this.render, this );
			this.model.on( 'destroy', this.remove, this );
			this.model.on( 'visible', this.toggleVisible, this );
		},

		// Re-render the form item.
		render: function() {
			console.log(this.template( this.model.toJSON() ));
			console.log(this.$el);
			this.$el.html( this.template( this.model.toJSON() ) );
			this.input = this.$('.edit');
			$('body').append(this.$el);
			return this;
		},

		// Switch this view into `"editing"` mode, displaying the input field.
		edit: function() {
			this.$el.addClass('editing');
			this.input.focus();
		},

		// Close the `"editing"` mode, saving changes to the form.
		close: function() {
			var value = this.input.val().trim();

			if ( value ) {
				this.model.save({ transcription: value });
			} else {
				this.clear();
			}

			this.$el.removeClass('editing');
		},

		// If you hit `enter`, we're through editing the item.
		updateOnEnter: function( e ) {
			if ( e.which === ENTER_KEY ) {
				this.close();
			}
		},

		// Remove the item, destroy the model from *localStorage* and delete its view.
		clear: function() {
			this.model.destroy();
		}
	});
});
