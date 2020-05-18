//var shutdown = false;
var recurringhandle = null; //A handle to the recurring function
recurringhandle = setInterval(get_moving, 1000); //start pinging the server
var bCalibration = false;

//create a new pen object attached to our canvas tag
var turtle = new Pen("mycanvas");
turtle.canvas.translate(0.5, 0.5);
turtle.pensize(3);
turtle.penstyle("#000");
turtle.pendown();
turtle.jump(240,320);


function shutdownserver(){
    clearInterval(recurringhandle);
    setTimeout(() => { console.log("Shutting down"); }, 1000);
    JSONrequest('/shutdown','POST');
    shutdown = true;
}

function draw_path(result){
    console.log(result);
    turtle.angle(result.heading);
    turtle.go(result.duration*10).stroke();
}

function draw_path_automated(result){
    console.log(result);
    if (result.command == "auto moving forward")
    {
        turtle.angle(result.heading);
        turtle.go(1.5*10).stroke();
    }
}

function command_test(result) {
    if (result.currentcommand == "auto moving forward")
    {
        JSONrequest('/getmovement','POST', draw_path_automated);
    }
}

//This recurring function gets data using JSON, note it cant be used while calibration
function get_moving() {
    if (bCalibration == false)
    {
        JSONrequest('/getcurrentcommand','POST', command_test);
    }
}
