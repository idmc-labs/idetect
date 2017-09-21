$( document ).ready(function(){


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