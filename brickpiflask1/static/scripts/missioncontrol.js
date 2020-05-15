//var shutdown = false;
var recurringhandle = null; //A handle to the recurring function
recurringhandle = setInterval(get_moving, 5000); //start pinging the server
var bCalibration = false;

//create a new pen object attached to our canvas tag
var turtle = new Pen("mycanvas");
turtle.canvas.translate(0.5, 0.5);
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

function draw_path(result){
    console.log(result);
    turtle.angle(result.heading);
    turtle.go(result.duration*20).stroke();
}

function draw_path_automated(result){
    console.log(result);
    if (result.command == "moving forward")
    {
        turtle.angle(result.heading);
        turtle.go(0.2*20).stroke();
    }
}

//This recurring function gets data using JSON, note it cant be used while calibration
function get_moving() {
    if (bCalibration == false)
    {
        JSONrequest('/getmovement','POST', draw_path_automated); //Once data is received it is passed to the drawchart function
    }
}
