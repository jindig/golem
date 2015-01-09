from golem.task.TaskBase import Task, TaskHeader, TaskBuilder
from golem.task.TaskState import SubtaskStatus
from golem.resource.Resource import prepareDeltaZip
from golem.environments.Environment import Environment

from examples.gnr.RenderingDirManager import getTmpPath

import os
import logging
import time

logger = logging.getLogger(__name__)

##############################################
def checkSubtaskIdWrapper( func ):
    def checkSubtaskId( *args, **kwargs):
        task = args[0]
        subtaskId = args[1]
        if subtaskId not in task.subTasksGiven:
            logger.error( "This is not my subtask {}".format( subtaskId ) )
            return False
        return func( *args, **kwargs )
    return checkSubtaskId

##############################################
class GNRTaskBuilder( TaskBuilder ):
    #######################
    def __init__( self, clientId, taskDefinition, rootPath ):
        self.taskDefinition = taskDefinition
        self.clientId       = clientId
        self.rootPath       = rootPath

    #######################
    def build( self ):
        pass

##############################################
class GNRSubtask():
    #######################
    def __init__(self, subtaskId, startChunk, endChunk):
        self.subtaskId = subtaskId
        self.startChunk = startChunk
        self.endChunk = endChunk

##############################################
class GNROptions:
    #######################
    def __init__( self ):
        self.environment = Environment()

    #######################
    def addToResources( self, resources ):
        return resources

    #######################
    def removeFromResources( self, resources ):
        return resources

##############################################
class GNRTask( Task ):
    #####################
    def __init__( self, srcCode, clientId, taskId, ownerAddress, ownerPort, environment,
                  ttl, subtaskTtl, resourceSize, estimatedMemory ):
        th = TaskHeader( clientId, taskId, ownerAddress, ownerPort, environment,
                         ttl, subtaskTtl, resourceSize, estimatedMemory)
        Task.__init__( self, th, srcCode )

        self.taskResources = []

        self.totalTasks = 0
        self.lastTask = 0

        self.numTasksReceived = 0
        self.subTasksGiven = {}
        self.numFailedSubtasks = 0

        self.fullTaskTimeout = 2200
        self.countingNodes = {}

    #######################
    def initialize( self ):
        pass

    #######################
    def restart ( self ):
        self.numTasksReceived = 0
        self.lastTask = 0
        self.subTasksGiven.clear()

        self.numFailedSubtasks = 0
        self.header.lastChecking = time.time()
        self.header.ttl = self.fullTaskTimeout


    #######################
    def getChunksLeft( self ):
        return (self.totalTasks - self.lastTask) + self.numFailedSubtasks

    #######################
    def getProgress( self ):
        return float( self.lastTask ) / self.totalTasks

    ########################
    @checkSubtaskIdWrapper
    def subtaskFailed( self, subtaskId, extraData ):
        self.numFailedSubtasks += 1
        self.subTasksGiven[ subtaskId ]['status'] = SubtaskStatus.failure

    #######################
    def needsComputation( self ):
        return (self.lastTask != self.totalTasks) or (self.numFailedSubtasks > 0)

    #######################
    def finishedComputation( self ):
        return self.numTasksReceived == self.totalTasks

    #######################
    def computationStarted( self, extraData ):
        pass

    #######################
    def getTotalTasks( self ):
        return self.totalTasks

    #######################
    def getTotalChunks( self ):
        return self.totalTasks

    #######################
    def getActiveTasks( self ):
        return self.lastTask

    #######################
    def getActiveChunks( self ):
        return self.lastTask

    #######################
    def prepareResourceDelta( self, taskId, resourceHeader ):
        if taskId == self.header.taskId:
            commonPathPrefix = os.path.commonprefix( self.taskResources )
            commonPathPrefix = os.path.dirname( commonPathPrefix )
            dirName = commonPathPrefix #os.path.join( "res", self.header.clientId, self.header.taskId, "resources" )
            tmpDir = getTmpPath(self.header.clientId, self.header.taskId, self.rootPath)


            if not os.path.exists( tmpDir ):
                os.makedirs( tmpDir )

            if os.path.exists( dirName ):
                return prepareDeltaZip( dirName, resourceHeader, tmpDir, self.taskResources )
            else:
                return None
        else:
            return None

    #######################
    def abort ( self ):
        pass

    #######################
    def updateTaskState( self, taskState ):
        pass

    #######################
    @checkSubtaskIdWrapper
    def verifySubtask( self, subtaskId ):
       return self.subTasksGiven[ subtaskId ]['status'] == SubtaskStatus.finished

    #######################
    def verifyTask( self ):
        return self.finishedComputation()

    #######################
    @checkSubtaskIdWrapper
    def getPriceMod( self, subtaskId ):
        return 1

    #######################
    @checkSubtaskIdWrapper
    def restartSubtask( self, subtaskId ):
        if subtaskId in self.subTasksGiven:
            if self.subTasksGiven[ subtaskId ][ 'status' ] == SubtaskStatus.starting:
                self._markSubtaskFailed( subtaskId )
            elif self.subTasksGiven[ subtaskId ][ 'status' ] == SubtaskStatus.finished :
                self._markSubtaskFailed( subtaskId )
                tasks = self.subTasksGiven[ subtaskId ]['endTask'] - self.subTasksGiven[ subtaskId  ]['startTask'] + 1
                self.numTasksReceived -= tasks

    #######################
    @checkSubtaskIdWrapper
    def shouldAccept(self, subtaskId):
        if self.subTasksGiven[ subtaskId ][ 'status' ] != SubtaskStatus.starting:
            return False
        return True

    #######################
    @checkSubtaskIdWrapper
    def _markSubtaskFailed( self, subtaskId ):
        self.subTasksGiven[ subtaskId ]['status'] = SubtaskStatus.failure
        self.countingNodes[ self.subTasksGiven[ subtaskId ][ 'clientId' ] ] = -1
        self.numFailedSubtasks += 1

