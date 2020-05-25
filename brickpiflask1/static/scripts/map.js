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

function go_through_events(results){
    if (results != "no events"){
        var i = 0;
        var h = 1;
        var e = 2;
        console.log(results.length)
        while (i < results.length) {
            console.log(results);
            var eventtype = results[i];
            var elapsedtime = results[e];
            var heading = results[h];
            console.log(eventtype);
            if (eventtype == "Moving Forward" || eventtype == "Auto Moving Forward"){
                turtle.angle(heading);
                turtle.go(10*elapsedtime).stroke();
            }
            var i = i + 3;
            var h = h + 3;
            var e = e + 3;
        }
    }
}

JSONrequest('/getevents','POST', go_through_events);

