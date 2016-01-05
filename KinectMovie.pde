/**
 * KinectMovie
 */

import processing.video.*;
import java.util.*;
import java.util.Random;
import java.io.*;
import java.net.*;

Movie mov = null;
Movie movPreload = null;

FileClipPart movFileParts;
FileClipPart movPreloadFileParts;

String stillOrMoving = "still";
int stillOrMovingCount = 0;
int stillOrMovingMax = 3;

int peopleLastTime = 0;

Map<String, Long> dictionaryClipLastPlayed = new HashMap<String, Long>();

Process procScriptWhile;
executeWhilePlaying myexecuteWhilePlaying;
Thread t;

void setup() {
  size(1920, 1080);
  //frame.setResizable(true);
  surface.setResizable(true);
  background(0);
  fill(0);
  rect(0, 0, width, height);

  loadNextMovie();
  playNextMovie();
}

void movieEvent(Movie movie) {
  mov.read();

  if (((mov.duration() - mov.time()) <= 2) && movPreload == null) {
    loadNextMovie();
  }

  if ((mov.duration() - mov.time()) <= 0.1) {
    playNextMovie();
  }
}

void playNextMovie() {
  println("playNextMovie()");
  mov = null;
  mov = movPreload;

  //Clear surface
  background(255);
  fill(0);
  rect(0, 0, width, height);
  redraw();

  if (movFileParts != null && movFileParts.RunScriptAfter.length() > 0) {
    println("RunScriptAfter " + movFileParts.RunScriptAfter);
    executeAndWait(movFileParts.RunScriptAfter);
  }

  movFileParts = movPreloadFileParts;

  if (movFileParts != null && movFileParts.RunScriptBefore.length() > 0) {
    println("RunScriptBefore " + movFileParts.RunScriptBefore);
    executeAndWait(movFileParts.RunScriptBefore);
  }

  if (procScriptWhile != null) {
    try {
      println("procScriptWhile.destroy");
      procScriptWhile.destroy();

      println("procScriptWhile.waitFor");
      procScriptWhile.waitFor();

      println("procScriptWhile = null");
      procScriptWhile = null;

      println("t = null");
      t = null;

      println("myexecuteWhilePlaying = null");
      myexecuteWhilePlaying = null;
    } catch (Exception e) {
      e.printStackTrace();
    }
  }

  if (movFileParts != null && movFileParts.RunScriptWhile.length() > 0) {
    println("RunScriptWhile " + movFileParts.RunScriptWhile);
    myexecuteWhilePlaying = new executeWhilePlaying(movFileParts.RunScriptWhile);
    t = new Thread(myexecuteWhilePlaying);
    t.start();
  }

  mov.play();
  movPreload = null;

  //Extra forwardspeed simplifies dubuging
  mov.speed(5);

  //Volume
  mov.volume(1);
}

void loadNextMovie() {
  println("loadNextMovie()");
  //ArrayList<File> filesList = filesToArrayList("/Users/viktorkarlsson/Desktop/KinectMovie/data");
  //ArrayList<File> filesList = filesToArrayList("/media/682E-929C/KinectMovie/data");
  ArrayList<File> filesList = filesToArrayList("/home/exxoz/Dropbox/Projects/Biosfären/KinectMovie/data");
  String choosenClip;
  choosenClip = chooseClip(filesList);
  //println("choosenClip: " + choosenClip);

  movPreload = new Movie(this, choosenClip);
  println("Loaded next movie: " + choosenClip + "\n");
}

String chooseClip(ArrayList<File> filesList) {
  int iPersons = getKinectPersons();
  int iPersonsDiff = iPersons - peopleLastTime;
  peopleLastTime = iPersons;
  println("People in now: "+iPersons+" diff: "+iPersonsDiff);

  calcStillOrMoving();

  List<ClipInfo> clipInfosPoints = new ArrayList<ClipInfo>();

  Long lNow = System.currentTimeMillis();

  //ArrayList<File> filesCandidatesList = new ArrayList<File>();
  for(File f : filesList){
    FileClipPart FileParts = new FileClipPart(f.getName());
    if (FileParts.Valid == true) {
      ClipInfo a = new ClipInfo();
      a.file = f;
      a.clipPart = FileParts;
      //println(a.file.getPath());

      //Still/Moving
      if (stillOrMoving.equals(a.clipPart.StillMoving)) {
        a.points += 100;
      }

      //Ökande/minskande
      if (iPersonsDiff == 0) {
        //Om ingen diff; använd samma land som förra gången
        if (movPreloadFileParts != null && a.clipPart.Land.equals(movPreloadFileParts.Land)) {
          a.points += 100;
        }
      } else {
        if (iPersonsDiff > 0) {
          if (a.clipPart.Land.equals("ar") || a.clipPart.Land.equals("arst")) {
            a.points += 100;
          }
        } else {
          if (a.clipPart.Land.equals("st") || a.clipPart.Land.equals("arst")) {
            a.points += 100;
          }
        }
      }

      //Antal personer
      if (iPersons >= a.clipPart.PersonsMin) {
        if (iPersons <= a.clipPart.PersonsMax) {
          a.points += 100;
        }
      }

      //Clip timeout
      //Map<String, Long> dictionaryClipLastPlayed = new HashMap<String, Long>();
      Long lastPlayed = dictionaryClipLastPlayed.get(a.file.getPath());
      if (lastPlayed == null) {
        a.points += 100;
      } else {
        Long diffLastPlayed = lNow - lastPlayed;
        diffLastPlayed = LimitUpper(diffLastPlayed, 500000L); //Limit the lastplayed
        float ratio = diffLastPlayed / 500000f;
        int point = Math.round(100*ratio);
        a.points += point;
      }

      //Random
      a.points += randInt(0, 10);

      clipInfosPoints.add(a);
    }
  }

  //Sort points Desc
  ClipInfoComparator comparator = new ClipInfoComparator();
  Collections.sort(clipInfosPoints, comparator);

  //Choose the file with most points
  //println(clipInfosPoints.get(0).file.getPath());
  dictionaryClipLastPlayed.put(clipInfosPoints.get(0).file.getPath(), lNow);
  movPreloadFileParts = clipInfosPoints.get(0).clipPart;
  return(clipInfosPoints.get(0).file.getPath());
}

Long LimitUpper(Long value, Long upperLimit) {
  Long out = value;
  if (out > upperLimit) {
    out = upperLimit;
  }
  return(out);
}

void calcStillOrMoving() {
  stillOrMovingCount += 1;
  if (stillOrMovingCount > stillOrMovingMax) {
    //Time to switch still/moving
    if (stillOrMoving.equals("still")) {
      stillOrMoving = "moving";
    } else {
      stillOrMoving = "still";
    }

    //Reset counter and choose new max
    stillOrMovingCount = 0;
    stillOrMovingMax = randInt(2, 3);
    println("Time to switch to " + stillOrMovingMax + " " + stillOrMoving);
  }
}

public class ClipInfo {
  public File file;
  public FileClipPart clipPart;
  public int points;
}

public class ClipInfoComparator implements Comparator<ClipInfo> {
  @Override
  public int compare(ClipInfo clip1, ClipInfo clip2) {
    return Integer.compare(clip2.points, clip1.points);
  }
}

ArrayList filesToArrayList() {
  return(filesToArrayList(dataPath("")));
}
ArrayList filesToArrayList(String path) {
  ArrayList<File> filesList = new ArrayList<File>();
  String folderPath = path;
  if (folderPath != null) {
    File file = new File(folderPath);
    File[] files = file.listFiles();
    for (int i = 0; i < files.length; i++) {
      filesList.add(files[i]);
    }
  }
  return(filesList);
}

int getKinectPersons() {
  String sHTML;
  //sHTML = getHTML("http://192.168.4.158:8080/");
  sHTML = getHTML("http://192.168.4.20:5000/");
  //println(sHTML);

  int iPersons = 0;
  //println(sHTML.length());
  if (isNumeric(sHTML)) {
    iPersons = Integer.parseInt(sHTML);
  } else {
    iPersons = 0;
  }
  //println(iPersons);

  return(iPersons);
}

public static int randInt(int min, int max) {
    // NOTE: Usually this should be a field rather than a method
    // variable so that it is not re-seeded every call.
    Random rand = new Random();

    // nextInt is normally exclusive of the top value,
    // so add 1 to make it inclusive
    int randomNum = rand.nextInt((max - min) + 1) + min;

    return randomNum;
}

public String getHTML(String urlToRead) {
  URL url;
  HttpURLConnection conn;
  BufferedReader rd;
  String line;
  StringBuilder result = new StringBuilder();
  try {
    url = new URL(urlToRead);
    conn = (HttpURLConnection) url.openConnection();
    conn.setRequestMethod("GET");
    conn.setConnectTimeout(1000);
    conn.setReadTimeout(1000);
    rd = new BufferedReader(new InputStreamReader(conn.getInputStream()));
    while ((line = rd.readLine()) != null) {
      result.append(line);
    }
    rd.close();
  } catch (IOException e) {
    //e.printStackTrace();
    return("");
  } catch (Exception e) {
    //e.printStackTrace();
    return("");
  }
  return result.toString();
}

public static boolean isNumeric(String str) {
  try {
    double d = Double.parseDouble(str);
  }
  catch(NumberFormatException nfe) {
    return false;
  }
  return true;
}

public class FileClipPart {
  //Filename-formating:
  //MinPersons-MaxPersons-RunScriptBefore-RunScriptWhile-RunScriptAfter-Sverige/Uganda-Still/Moving-Comment.ext
  // MinPersons - to activate clip
  // MaxPersons - to activate clip
  // RunScriptBefore - Script to be executed before clip
  // RunScriptWhile - Script to be executed while playing clip
  // RunScriptAfter - Script to be executed after clip
  // Sverige/Uganda Ställberg/Aremo
  // Still/Moving
  //Comment - Any freeetext, like 'Vaskar guld'
  //ext - Extension of filename, ex. mp4, mov, avi
  public String Filename;
  public Boolean Valid;
  public int PersonsMin;
  public int PersonsMax;
  public String RunScriptBefore;
  public String RunScriptWhile;
  public String RunScriptAfter;
  public String Land;
  public String StillMoving;
  public String Comment;
  public String Extension;

  FileClipPart (String sFilename) {
    Filename = sFilename;
    String[] sFileParts = Filename.split("-");
    if (sFileParts.length != 8) {
      Valid = false;
      //println("Not 8 args " + Filename);
    } else {
      Valid = true;
      if (isNumeric(sFileParts[0])) {
        PersonsMin = Integer.parseInt(sFileParts[0]);
      } else {
        Valid = false;
      }

      if (isNumeric(sFileParts[1])) {
        PersonsMax = Integer.parseInt(sFileParts[1]);
      } else {
        Valid = false;
      }

      RunScriptBefore = sFileParts[2];
      RunScriptWhile = sFileParts[3];
      RunScriptAfter = sFileParts[4];

      Land = sFileParts[5];
      StillMoving = sFileParts[6];

      Comment = sFileParts[7];
    }
  }
}

void executeAndWait(String filename) {
  try {
    String sPath;
    sPath = dataPath(filename);

    Runtime rt = Runtime.getRuntime();
    Process proc = rt.exec(sPath);
    InputStream stdin = proc.getInputStream();
    InputStreamReader isr = new InputStreamReader(stdin);
    BufferedReader br = new BufferedReader(isr);
    String line = null;
    //System.out.println("<OUTPUT>");
    while ( (line = br.readLine()) != null) {
      println(line);
    }
    //System.out.println("</OUTPUT>");
    int exitVal = proc.waitFor();
    //System.out.println("Process exitValue: " + exitVal);
  } catch (Exception e) {
    //e.printStackTrace();
  }
}

public class executeWhilePlaying implements Runnable {
  //procScriptWhile
  private String filename;

  public executeWhilePlaying(String sFilename) {
    println("filename = sFilename");
    println(filename);
    filename = sFilename;
  }

  public void run() {
    try {
      println("run");
      String sPath;
      sPath = dataPath(filename);

      Runtime rt = Runtime.getRuntime();
      procScriptWhile = rt.exec(sPath);
      InputStream stdin = procScriptWhile.getInputStream();
      InputStreamReader isr = new InputStreamReader(stdin);
      BufferedReader br = new BufferedReader(isr);
      String line = null;
      //System.out.println("<OUTPUT>");
      while ( (line = br.readLine()) != null) {
        println(line);
      }
    } catch (Exception e) {
      //e.printStackTrace();
    }
  }
}

void printDuration() {
  fill(255);
  text("Time: " + nfc(mov.time(), 2), 10, 30);
  text("Duration: " + nfc(mov.duration(), 2), 10, 50);
}

void draw() {
  if (mov != null) {
    image(mov, 0, 0);
    printDuration();
  } //<>//
}
