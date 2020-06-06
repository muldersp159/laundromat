var bCalibration = false;

function shutdownserver(){
    clearInterval(recurringhandle);
    setTimeout(() => { console.log("Shutting down"); }, 1000);
    JSONrequest('/shutdown','POST');
    shutdown = true;
}

function go_through_events(results){
    if (results.events != "no events"){
        var turtle = new Pen("mycanvas");
        turtle.canvas.translate(0.5, 0.5);
        turtle.pensize(3);
        turtle.penstyle("#000");
        turtle.pendown();
        turtle.jump(240,320);
        //creating the turtle that will draw the past path
        //only do it in this function because otherwise 
        //trying to get canvas which wont exist yet
        var i = 0;
        var h = 1;
        var e = 2;
        //use these to select list items
        while (i < results.events.length) {
            var eventtype = results.events[i];
            var elapsedtime = results.events[e];
            var heading = results.events[h];
            if (eventtype == "Moving Forward" || eventtype == "Auto Moving Forward"){
                turtle.set();
                turtle.begin();
                turtle.home();
                turtle.pensize(3);
                turtle.penstyle("#000");
                //have to create a new line for each stroke 
                //to have different colour parts
                turtle.angle(heading);
                turtle.go(15*elapsedtime).stroke();
            }
            
            else if (eventtype == "Fire Detected"){
                //draws orange triangle
                turtle.penup();
                turtle.angle(heading);
                turtle.go(8);
                //moving in front of the current 
                //line a bit so no overlap
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
                //draws green box
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
                //draws small red box
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
            }
            var i = i + 3;
            var h = h + 3;
            var e = e + 3;
        }
    }
}

JSONrequest('/getevents','POST', go_through_events);
//passes all events into the go_through_events function

