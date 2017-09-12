$( document ).ready(function(){

	// window.setTimeout(function() {
	// 	    $(".alert").fadeTo(1000, 0).slideUp(1000, function(){
	// 	        $(this).remove(); 
	// 	    });
	// 	}, 4000);

	$('input[name="add_url"]').click(function(e){
		e.preventDefault();
        $.ajax({
                url: 'add_url',
                data: $('form[name="add_url"]').serialize(),
                type: 'POST',
                success: function(response) {
                   msg = '<div class="alert alert-success" role="alert">';
                   msg += '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>';
                   msg += 'Successfully added: ';
                   msg += $("input#add_url_field").val();
                   msg += "</div>";
                   $("input#add_url_field").val("");
                   $(msg).insertBefore('form[name="add_url"]');
                },
                error: function(error) {
                    msg = '<div class="alert alert-danger" role="alert">';
                    msg += '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>';
                    msg += 'Something went wrong. Please try again.</div>';
                    $(msg).insertBefore('form[name="add_url"]');
                }
          });
	});

	$('input[name="search_url"]').click(function(e){
		e.preventDefault();
        $.ajax({
                url: 'search_url',
                data: $('form[name="search_url"]').serialize(),
                type: 'GET',
                success: function(response) {
                   	window.location.replace("article/" + response["doc_id"])
                },
                error: function(error) {
                    msg = '<div class="alert alert-danger" role="alert">';
                    msg += '<button type="button" class="close" data-dismiss="alert" aria-label="Close"><span aria-hidden="true">&times;</span></button>';
                    msg += 'The requested URL was not found.</div>';
                    $(msg).insertBefore('form[name="search_url"]');
                }
          });
	});

});