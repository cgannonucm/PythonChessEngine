from asyncio.log import logger
from unittest import suite
from moveengine import *
import time
import unittest
from multiprocessing import Process
import logging

class TestPermute(unittest.TestCase):
    """Test cases from chessprogramming.org/Perft_Results"""

    cache = None
    moveengine = None
    
    def fen_test(self,fen:str,depth:int,states:int,name:str):
        

        
        self.moveengine.set_fen(fen)

        t1 = time.perf_counter()
        perft_result = self.moveengine.perft(depth)
        self.assertEqual(perft_result,states,f"testing depth {depth}")
        t2 = time.perf_counter()

        self.print_test_msg(name)
        logging.info(f"Testing depth {depth}")
        logging.info(f"Found {perft_result} nodes in {(t2-t1):.2f} (s)")
        logging.info("-----------------------------------------")

    def print_test_msg(self,pos_num):
        logging.info(f"Testing Position {pos_num} https://www.chessprogramming.org/Perft_Results")
        pass


    def setUp(self) -> None:
        logging.basicConfig(level=logging.DEBUG)
        self.cache = MoveCache()
        board = BoardIO.from_fen(FEN.START_POS)
        self.moveengine = MoveEngine(board,self.cache)

        return super().setUp()

class TestProcess(Process):
    """https://medium.com/tauk-blog/parallel-execution-with-unittest-in-python-feb655d52c54"""

    def __init__(self,test):
        Process.__init__(self)
        self.test = test

    def run(self):
        logging.basicConfig(level=logging.DEBUG)

        suite = unittest.TestSuite()
        suite.addTest(self.test)

        unittest.TextTestRunner().run(suite)
            

class TestStartPos(TestPermute):
    
    def runTest(self):

        name = ": Starting Position"
        self.fen_test(FEN.START_POS,1,20,name)
        self.fen_test(FEN.START_POS,2,400,name)
        self.fen_test(FEN.START_POS,3,8902,name)
        self.fen_test(FEN.START_POS,4,197281,name)
        self.fen_test(FEN.START_POS,5,4865609,name)
        self.fen_test(FEN.START_POS,6,119060324,name)

class TestPos2(TestPermute):

    def runTest(self):
        name = "2"
        self.fen_test(FEN.POS_2,1,48,name)
        self.fen_test(FEN.POS_2,2,2039,name)
        self.fen_test(FEN.POS_2,3,97862,name)
        self.fen_test(FEN.POS_2,4,4085603,name)
        self.fen_test(FEN.POS_2,5,193690690,name)


class TestPos3(TestPermute):

    def runTest(self):
        name = "3"
        self.fen_test(FEN.POS_3,1,14,name)
        self.fen_test(FEN.POS_3,2,191,name)
        self.fen_test(FEN.POS_3,3,2812,name)
        self.fen_test(FEN.POS_3,4,43238,name)
        self.fen_test(FEN.POS_3,5,674624,name)
        self.fen_test(FEN.POS_3,6,11030083,name)

class TestPos4(TestPermute):
    
    def runTest(self):
        name = "4"
        self.fen_test(FEN.POS_4,1,6,name)
        self.fen_test(FEN.POS_4,2,264,name)
        self.fen_test(FEN.POS_4,3,9467,name)
        self.fen_test(FEN.POS_4,4,422333,name)
        self.fen_test(FEN.POS_4,5,15833292,name)
        self.fen_test(FEN.POS_4,6,706045033,name)

class TestPos5(TestPermute):

    def runTest(self):
        name = "5"
        self.fen_test(FEN.POS_5,1,44,name)
        self.fen_test(FEN.POS_5,2,1486,name)
        self.fen_test(FEN.POS_5,3,62379,name)
        self.fen_test(FEN.POS_5,4,2103487,name)
        self.fen_test(FEN.POS_5,5,89941194,name)

class TestPos6(TestPermute):

    def runTest(self):
        name = "6"
        self.fen_test(FEN.POS_6,1,46,name)
        self.fen_test(FEN.POS_6,2,2079,name)
        self.fen_test(FEN.POS_6,3,89890,name)
        self.fen_test(FEN.POS_6,4,3894594,name)
        self.fen_test(FEN.POS_6,5,164075551,name)



if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)


    t1 = TestProcess(TestStartPos())
    t2 = TestProcess(TestPos2())
    t3 = TestProcess(TestPos3())
    t4 = TestProcess(TestPos4())
    t5 = TestProcess(TestPos5())
    t6 = TestProcess(TestPos6())

    t1.start()
    time.sleep(0.00001)
    t2.start()
    time.sleep(0.00001)
    t3.start()
    time.sleep(0.00001)
    t4.start()
    time.sleep(0.00001)
    t5.start()
    time.sleep(0.00001)
    t6.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()
    t5.join()
    t6.join()

    input()



