//var shutdown = false;
var recurringhandle = null;  //can be used to delete recurring function if you want

//create a new pen object attached to our canvas tag
var turtle = new Pen("mycanvas");
turtle.canvas.translate(.5, .5);
turtle.pensize(3);
turtle.penstyle("#000");
turtle.pendown();
turtle.jump(200,200);


function shutdownserver(){
    clearInterval(recurringhandle);
    setTimeout(() => { console.log("Shutting down"); }, 1000);
    JSONrequest('/shutdown','POST');
    shutdown = true;
}

funciton draw_path(result)
{
    console.log(result);
    turtle.angle(result.heading);
    turtle.go(result.elapsedtime*20).stroke();
}

//THis recurring function gets data using JSON
function get_current_command() {
    if (shutdown == false)
    {
        JSONrequest('/getcurrentcommand','POST', writecurrentcommand); //Once data is received it is passed to the writecurrentcommand
    }
}

//with received json data, send to page
function writecurrentcommand(results) {
    document.getElementById('message').innerHTML = results.currentcommand;
}

