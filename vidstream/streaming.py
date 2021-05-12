"""
This module implements the main functionality of vidstream.

Author: Florian Dedov from NeuralNine
YouTube: https://www.youtube.com/c/NeuralNine
"""

__author__ = "Florian Dedov, NeuralNine"
__email__ = "mail@neuralnine.com"
__status__ = "planning"

import cv2
import pyautogui
import numpy as np

import socket
import pickle
import struct
import threading


class StreamingServer:
    """
    Class for the streaming server.

    Attributes
    ----------

    Private:

        __host : str
            host address of the listening server
        __port : int
            port on which the server is listening
        __slots : int
            amount of maximum avaialable slots (not ready yet)
        __used_slots : int
            amount of used slots (not ready yet)
        __quit_key : chr
            key that has to be pressed to close connection
        __running : bool
            inicates if the server is already running or not
        __block : Lock
            a basic lock used for the synchronization of threads
        __server_socket : socket
            the main server socket


    Methods
    -------

    Private:

        __init_socket : method that binds the server socket to the host and port
        __server_listening: method that listens for new connections
        __client_connection : main method for processing the client streams

    Public:

        start_server : starts the server in a new thread
        stop_server : stops the server and closes all connections
    """

    # TODO: Implement slots functionality
    def __init__(self, host, port, slots=8, quit_key='q'):
        """
        Creates a new instance of StreamingServer

        Parameters
        ----------

        host : str
            host address of the listening server
        port : int
            port on which the server is listening
        slots : int
            amount of avaialable slots (not ready yet) (default = 8)
        quit_key : chr
            key that has to be pressed to close connection (default = 'q')
        """
        self.__host = host
        self.__port = port
        self.__slots = slots
        self.__used_slots = 0
        self.__running = False
        self.__quit_key = quit_key
        self.__block = threading.Lock()
        self.__server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__init_socket()

    def __init_socket(self):
        """
        Binds the server socket to the given host and port
        """
        self.__server_socket.bind((self.__host, self.__port))

    def start_server(self):
        """
        Starts the server if it is not running already.
        """
        if self.__running:
            print("Server is already running")
        else:
            self.__running = True
            server_thread = threading.Thread(target=self.__server_listening)
            server_thread.start()

    def __server_listening(self):
        """
        Listens for new connections.
        """
        self.__server_socket.listen()
        while self.__running:
            self.__block.acquire()
            connection, address = self.__server_socket.accept()
            if self.__used_slots >= self.__slots:
                print("Connection refused! No free slots!")
                connection.close()
                self.__block.release()
                continue
            else:
                self.__used_slots += 1
            self.__block.release()
            thread = threading.Thread(target=self.__client_connection, args=(connection, address,))
            thread.start()

    def stop_server(self):
        """
        Stops the server and closes all connections
        """
        if self.__running:
            self.__running = False
            closing_connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            closing_connection.connect((self.__host, self.__port))
            closing_connection.close()
            self.__block.acquire()
            self.__server_socket.close()
            self.__block.release()
        else:
            print("Server not running!")


    def __recvData(self, connection, address,headerSize,clientType):

        header=b""
        break_loop = False
        leftToRecive=headerSize
        # if clientType==1:
        #     if self.currentStack[self.currentFrame]:
        #         print('getting:',self.currentFrame)
        #         return self.currentStack[self.currentFrame],break_loop



        while len(header) < headerSize:
            if leftToRecive<4096:
                received = connection.recv(leftToRecive)
            else:
                received = connection.recv(4096)
                leftToRecive-=4096
            if received == b'':
                connection.close()
                self.__used_slots -= 1
                break_loop = True
                break
            header += received

        if break_loop:
            return break_loop

        packed_msg_size = header[:headerSize]
        data = b""

        header = struct.unpack(">LLL", packed_msg_size)
        msg_size=header[2]
        leftToRecive=msg_size

        while len(data) < msg_size:
            if leftToRecive<4096:
                data += connection.recv(leftToRecive)
            else:
                data += connection.recv(4096)
                leftToRecive-=4096
        frame_data = data[:msg_size]


        return frame_data,break_loop
    def __sendData(self,data=None):

            if data:
                status='getFrame'.encode('utf-8')
                val1=data[0]
                val2=data[1]
            else:
                status='OK'.encode('utf-8')
                val=self.currentFrame
                val=0
            # if self

            packedData=struct.pack('>16sLL',status,val1,val2)

            self.connection.send(packedData)



    def trackbarFuntion(self,val):
        if self.currentStack[val-1]==None:
            self.currentFrame=val-1
        #
        sendData=[self.currentFrame,val-1]
        self.__sendData(sendData)


    def __handleVideoPacket(self,windowName,totalFrames):
        print(windowName)

        cv2.namedWindow(windowName,cv2.WINDOW_AUTOSIZE)
        trackbarName='Frame No:'
        cv2.createTrackbar(trackbarName,windowName,0,totalFrames+1,self.trackbarFuntion)

    def _recvsetupInfo(self,payload_size,connection,address):
        setupInfo=connection.recv(payload_size)
        if setupInfo:
            setupInfo = struct.unpack(">LLL", setupInfo)
            clientType=setupInfo[0]
            print('clientType:',clientType)
            if clientType==1:
                totalFrames=setupInfo[1]
                print('toto',totalFrames)
                self.__handleVideoPacket(str(address),totalFrames)
                self.currentFrame=0
                self.currentStack=[None for i in range(totalFrames)] #can't create list for 10 hours video Improve on that

                return clientType

    def __processFrame(self,frame_data,clientType,address):
        if clientType==1:
            cv2.setTrackbarPos('Frame No:',str(address),(int(self.currentFrame)+1))
            self.currentStack[self.currentFrame]=frame_data
            self.currentFrame+=1

    def __client_connection(self, connection, address):
        """
        Handles the individual client connections and processes their stream data.
        """
        self.connection=connection
        self.address=address
        payload_size = struct.calcsize('>LLL')
        data = b""
        clientType=self._recvsetupInfo(payload_size,connection,str(address))

        while self.__running:

            frame_data,break_loop=self.__recvData(connection,address,payload_size,clientType)

            frame = pickle.loads(frame_data, fix_imports=True, encoding="bytes")
            frame = cv2.imdecode(frame, cv2.IMREAD_COLOR)
            cv2.imshow(str(address), frame)


            self.__processFrame(frame_data,clientType,address)
            if cv2.waitKey(1) == ord(self.__quit_key):
                connection.close()
                self.__used_slots -= 1
                break


class StreamingClient:
    """
    Abstract class for the generic streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            inicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket


    Methods
    -------

    Private:

        __client_streaming : main method for streaming the client data

    Protected:

        _configure : sets basic configurations (overridden by child classes)
        _get_frame : returns the frame to be sent to the server (overridden by child classes)
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the client stream in a new thread
    """

    def __init__(self, host, port,packetType=None):
        """
        Creates a new instance of StreamingClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        """
        self.__host = host
        self.__port = port
        self._configure()
        self.__running = False
        self.__client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.packetType=packetType

    def _configure(self):
        """
        Basic configuration function.
        """
        self.__encoding_parameters = [int(cv2.IMWRITE_JPEG_QUALITY), 90]

    def _get_frame(self,data=None):
        """
        Basic function for getting the next frame.

        Returns
        -------

        frame : the next frame to be processed (default = None)
        """
        return None
    def _createHeader(self,packetLength):
        return None

    def _cleanup(self):
        """
        Cleans up resources and closes everything.
        """
        cv2.destroyAllWindows()
    def __sendData(self,size,data):
        header=self._createHeader(size)
        self.__client_socket.sendall(header + data)
    def _sendsetupInfo(self):
        return None
    def __recvData(self):
        calcsize= struct.calcsize('>16sLL')
        status=self.__client_socket.recv(calcsize)
        print(status)
        return struct.unpack(">16sLL", status)
    def __client_streaming(self):
        """
        Main method for streaming the client data.
        """
        self.__client_socket.connect((self.__host, self.__port))
        self.__client_socket.send(self._sendsetupInfo())
        frameInput=None
        while self.__running:
            frame = self._get_frame(frameInput)
            frameInput=None
            result, frame = cv2.imencode('.jpg', frame, self.__encoding_parameters)
            data = pickle.dumps(frame, 0)
            size = len(data)

            try:
                self.__sendData(size,data)
                data=self.__recvData()
                if data[0].decode('utf-8').rstrip('\x00')=='OK':
                    continue
                elif data[0].decode('utf-8').rstrip('\x00')=='getFrame':
                    frameInput=data[1:]

            except ConnectionResetError:
                self.__running = False
            except ConnectionAbortedError:
                self.__running = False
            except BrokenPipeError:
                self.__running = False

        self._cleanup()

    def start_stream(self):
        """
        Starts client stream if it is not already running.
        """

        if self.__running:
            print("Client is already streaming!")
        else:
            self.__running = True
            client_thread = threading.Thread(target=self.__client_streaming)
            client_thread.start()

    def stop_stream(self):
        """
        Stops client stream if running
        """
        if self.__running:
            self.__running = False
        else:
            print("Client not streaming!")


class CameraClient(StreamingClient):
    """
    Class for the camera streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            inicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __camera : VideoCapture
            the camera object
        __x_res : int
            the x resolution
        __y_res : int
            the y resolution


    Methods
    -------

    Protected:

        _configure : sets basic configurations
        _get_frame : returns the camera frame to be sent to the server
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the camera stream in a new thread
    """

    def __init__(self, host, port, x_res=1024, y_res=576):
        """
        Creates a new instance of CameraClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        x_res : int
            the x resolution
        y_res : int
            the y resolution
        """
        self.__x_res = x_res
        self.__y_res = y_res
        self.__camera = cv2.VideoCapture(0)
        self.packetType=0
        super(CameraClient, self).__init__(host, port,self.packetType)

    def _configure(self):
        """
        Sets the camera resultion and the encoding parameters.
        """
        self.__camera.set(3, self.__x_res)
        self.__camera.set(4, self.__y_res)
        super(CameraClient, self)._configure()

    def _get_frame(self,data=None):
        """
        Gets the next camera frame.

        Returns
        -------

        frame : the next camera frame to be processed
        """
        ret, frame = self.__camera.read()
        return frame

    def _cleanup(self):
        """
        Cleans up resources and closes everything.
        """
        self.__camera.release()
        cv2.destroyAllWindows()

    def _createHeader(self,packetLength):
        return struct.pack(">L",packetLength)
    def _sendsetupInfo(self):
        return None

class VideoClient(StreamingClient):
    """
    Class for the video streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            inicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __video : VideoCapture
            the video object
        __loop : bool
            boolean that decides whether the video shall loop or not


    Methods
    -------

    Protected:

        _configure : sets basic configurations
        _get_frame : returns the video frame to be sent to the server
        _cleanup : cleans up all the resources and closes everything

    Public:

        start_stream : starts the video stream in a new thread
    """

    def __init__(self, host, port, video, loop=True):
        """
        Creates a new instance of VideoClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        video : str
            path to the video
        loop : bool
            indicates whether the video shall loop or not
        """
        self.__video = cv2.VideoCapture(video)
        self.__loop = loop
        self.packetType=1
        super(VideoClient, self).__init__(host, port,self.packetType)

    def _configure(self):
        """
        Set video resolution and encoding parameters.
        """
        self.__video
        (3, 1024)
        self.__video.set(4, 576)
        super(VideoClient, self)._configure()

    def _get_frame(self,data=None):
        """
        Gets the next video frame.

        Returns
        -------

        frame : the next video frame to be processed
        """
        if data:
            self.__video.set(1,data[1])
        ret, frame = self.__video.read()
        return frame

    def _cleanup(self):
        """
        Cleans up resources and closes everything.
        """
        self.__video.release()
        cv2.destroyAllWindows()

    def _createHeader(self,packetLength):
        totalFrames = int(self.__video.get(cv2.CAP_PROP_FRAME_COUNT))
        currentFrameNo=int(self.__video.get(cv2.CAP_PROP_POS_FRAMES))
        header= struct.pack(">LLL",currentFrameNo,totalFrames,packetLength)
        return header

    def _sendsetupInfo(self):
        totalFrames = int(self.__video.get(cv2.CAP_PROP_FRAME_COUNT))
        return struct.pack(">LLL",self.packetType,totalFrames,0)


class ScreenShareClient(StreamingClient):
    """
    Class for the screen share streaming client.

    Attributes
    ----------

    Private:

        __host : str
            host address to connect to
        __port : int
            port to connect to
        __running : bool
            inicates if the client is already streaming or not
        __encoding_parameters : list
            a list of encoding parameters for OpenCV
        __client_socket : socket
            the main client socket
        __x_res : int
            the x resolution
        __y_res : int
            the y resolution


    Methods
    -------

    Protected:

        _get_frame : returns the screenshot frame to be sent to the server

    Public:

        start_stream : starts the screen sharing stream in a new thread
    """

    def __init__(self, host, port, x_res=1024, y_res=576):
        """
        Creates a new instance of ScreenShareClient.

        Parameters
        ----------

        host : str
            host address to connect to
        port : int
            port to connect to
        x_res : int
            the x resolution
        y_res : int
            the y resolution
        """
        self.__x_res = x_res
        self.__y_res = y_res
        self.packetType=2
        super(ScreenShareClient, self).__init__(host, port,self.packetType)

    def _get_frame(self,data=None):
        """
        Gets the next screenshot.

        Returns
        -------

        frame : the next screenshot frame to be processed
        """
        screen = pyautogui.screenshot()
        frame = np.array(screen)
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame = cv2.resize(frame, (self.__x_res, self.__y_res), interpolation=cv2.INTER_AREA)
        return frame
    def _createHeader(self,packetLength):
        return struct.pack(">L",packetLength)

    def _sendsetupInfo(self):
        return None
