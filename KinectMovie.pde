import processing.net.*;
import processing.video.*;

String HTTP_GET_REQUEST = "GET /";
String HTTP_HEADER = "HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n";

Server s;
Client c;
String input;

Movie mov = null;

void setup() 
{
  size(1920, 1080);
  surface.setResizable(true);
  background(0);
  fill(0);
  rect(0, 0, width, height);
  
  s = new Server(this, 6000);
}

void draw() 
{
  // Receive data from client
  c = s.available();
  if (c != null) {
    input = c.readString();
    input = input.substring(0, input.indexOf("\n")); // Only up to the newline
    
    if (input.indexOf(HTTP_GET_REQUEST) == 0) // starts with ...
    {
      c.write(HTTP_HEADER);  // answer that we're ok with the request and are gonna send html
      
      //GET /play/asdgfqwe-qwe23.mp4/ HTTP/1.1
      println(input);
      
      String[] sFileParts = input.split("/");
      
      String sCommand = sFileParts[1];
      String sPath = sFileParts[2];
      
      c.write("1");
      
      c.stop();
      
      if (sCommand.equals("play")) {
        println("Play " + sPath);
        if (mov != null) {
          mov.stop();
          mov = null;
          redrawScreen();
        }
        mov = new Movie(this, sPath);
        mov.play();
        mov.volume(1);
      }
      if (sCommand.equals("stop")) {
        println("Stop");
        if (mov != null) {
          mov.stop();
          mov = null;
          redrawScreen();
        }
      }
    }
  }
  
  if (mov != null) {
    image(mov, 0, 0);
  }
  
  if (mov != null) {
    if ((mov.duration() - mov.time()) <= 0.1) {
      println("Endofmovie");
      mov.stop();
      mov = null;
      redrawScreen();
    }
  }
}

void movieEvent(Movie m) {
    m.read();
}

void redrawScreen() {
  background(0);
  fill(0);
  rect(0, 0, width, height);
}