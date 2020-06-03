var bCalibration = false;

//create a new pen object attached to our canvas tag


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
        var i = 0;
        var h = 1;
        var e = 2;
        while (i < results.events.length) {
            var eventtype = results.events[i];
            var elapsedtime = results.events[e];
            var heading = results.events[h];
            if (eventtype == "Moving Forward" || eventtype == "Auto Moving Forward"){
                turtle.penstyle("#000")
                console.log("balck pen for moving forward")
                turtle.angle(heading);
                turtle.go(10*elapsedtime).stroke();
            }
            
            if (eventtype == "Fire Detected"){
                turtle.penup();
                turtle.angle(heading);
                turtle.go(2);
                turtle.pendown();
                turtle.penstyle("#ff9933");
                turtle.turn(-90)
                turtle.go(2.5).stroke();
                var t = 1;
                while (t < 3){
                    turtle.turn(120);
                    turtle.go(5).stroke();
                    t = t + 1
                }
                turtle.turn(120);
                turtle.go(2.5).stroke();
                turtle.turn(-90);
                turtle.penup();
                turtle.go(2);
                turtle.angle(heading);
                turtle.penstyle("#000");
                console.log("changing pen back to black")
                turtle.pendown();  
            }
            
            if (eventtype == "Victim Found"){
                turtle.penup();
                turtle.angle(heading);
                turtle.go(2);
                turtle.pendown();
                turtle.penstyle("#33cc33");
                turtle.turn(-90)
                turtle.go(2.5).stroke();
                var t = 1
                while (t < 4){
                    turtle.turn(90);
                    turtle.go(5).stroke();
                    t = t + 1
                }
                turtle.turn(90);
                turtle.go(2.5).stroke();
                turtle.turn(-90);
                turtle.penup();
                turtle.go(2);
                turtle.angle(heading);
                turtle.penstyle("#000");
                turtle.pendown();
            }
            var i = i + 3;
            var h = h + 3;
            var e = e + 3;
        }
    }
}

JSONrequest('/getevents','POST', go_through_events);

