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
    turtle.go(result.duration*15).stroke();
}

function draw_path_automated(result){
    console.log(result);
    if (eventtype == "Moving Forward" || eventtype == "Auto Moving Forward"){
        turtle.set();
        turtle.begin();
        turtle.home();
        turtle.pensize(3);
        turtle.penstyle("#000");
        turtle.angle(heading);
        turtle.go(15*elapsedtime).stroke();
    }
    
    else if (eventtype == "Fire Detected"){
        turtle.penup();
        turtle.angle(heading);
        turtle.go(8);
        turtle.set();
        turtle.begin();
        turtle.home();
        turtle.pensize(0);
        turtle.pendown();
        turtle.fillstyle("#ff9933");
        turtle.turn(-90)
        turtle.go(5).fill();
        var t = 1;
        while (t < 3){
            turtle.turn(120);
            turtle.go(10).fill();
            t = t + 1
        }
        turtle.turn(120);
        turtle.go(5).fill();
        turtle.turn(-90);
        turtle.penup();
        turtle.go(5);
        turtle.angle(heading);
        turtle.pendown();  
    }
    
    else if (eventtype == "Victim Found"){
        turtle.penup();
        turtle.angle(heading);
        turtle.go(8);
        turtle.set();
        turtle.begin();
        turtle.home();
        turtle.pensize(0);
        turtle.pendown();
        turtle.fillstyle("#33cc33");
        turtle.turn(-90)
        turtle.go(5).fill();
        var t = 1
        while (t < 4){
            turtle.turn(90);
            turtle.go(10).fill();
            t = t + 1
        }
        turtle.turn(90);
        turtle.go(5).fill();
        turtle.turn(-90);
        turtle.penup();
        turtle.go(5);
        turtle.angle(heading);
        turtle.pendown();
    }
    
    else if (eventtype == "Junction Detected"){
        turtle.penup();
        turtle.angle(heading);
        turtle.set();
        turtle.begin();
        turtle.home();
        turtle.turn(180);
        turtle.go(4);
        turtle.pensize(0);
        turtle.pendown();
        turtle.fillstyle("#ff0000");
        turtle.turn(90)
        turtle.go(3).fill();
        var t = 1
        while (t < 4){
            turtle.turn(90);
            turtle.go(6).fill();
            t = t + 1
        }
        turtle.turn(90);
        turtle.go(3).fill();
        turtle.turn(-90);
        turtle.angle(heading);
        console.log("ollah");
    }
}

function command_test(result) {
    if (result.currentcommand == "Auto Moving Forward")
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
