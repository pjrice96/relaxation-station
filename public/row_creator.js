
var row_top =`<div class="card-body">
        <div class="container">
        <div class="container">	
        <div class="row">`;
var row_bottom_1 ='</div></div>';
var row_bottom_2 = '</div>';
var row_bottom_3 = '</div></div>';

function row_creator (video_list){
    var row_array = new Array();
    var card_list = card_creator(video_list);
    for (var g = 0; g<card_list.length; g++){
        if (g % 3 == 0){
            row_array.push(row_top);
            row_array.push(row_bottom_1);
        }
        row_array.push(card_list[g]);
        if (g % 3 == 1){
            row_array.push(row_bottom_2);
        }
        if (g % 3 == 2){
            row_array.push(row_bottom_3);
        }
    }
    row_array.join();
    return row_array;
    
}

    
    
        
var card_top = '<div class="col-md-4"> <div class="card mb-4 shadow-sm"> <iframe width="348" height="225" src="';
var card_middle = '" frameborder="0" allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe><div class="card-body"><p class="card-text">';
var card_bottom = '</p><div class="d-flex justify-content-between align-items-center"><div class="btn-group"><button type="button" class="btn btn-sm btn-outline-secondary">Like</button><button type="button" class="btn btn-sm btn-outline-secondary">Dislike</button></div><small class="text-muted">9 mins</small></div></div></div></div>';

function card_creator (video_list){
    var card_list = new Array();
    var list_len = video_list.length;
    for (var j =0; j<list_len; j++){
        var video_obj = video_list[j];
        var video_name = video_obj[1];
        var video_id = video_obj[0];
        var video_url = video_obj[2];
        var video_tags = video_obj[3];

        var card_str = card_top + video_url + card_middle + video_name + card_bottom;
        card_list.push(card_str);
        }
     return card_list;
     }
     

        
        
        
        //videos.video_id, videos.video_name, videos.video_url, user_video_map.video_tags