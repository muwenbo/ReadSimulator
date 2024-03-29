#!/bin/python

import sys
import re
import getopt
import random
import os
import math
import array
from Bio import SeqIO

# Classes
class Read:
    def __init__(self,readIndex,sequence,idPrefix,read1Len,read2Len,refChr, refStart):
        self.startPosition = readIndex
        self.id = '@'+idPrefix+'_SEQID' + str(readIndex)
        self.read1Len = read1Len
        self.read2Len = read2Len
        self.refStart = refStart
        self.refChr = refChr
        #self.errorRate = errorRate
        #self.score = self.scoreGenerator(subSequence)
        dynamicGap = min(random.sample(range(200,300),1)[0],len(sequence)-readIndex-read1Len-read2Len)
        newReadLen = read1Len + dynamicGap + read2Len
        subSequence = sequence[readIndex:readIndex + newReadLen]
        self.seq = array.array('u',subSequence).tolist()
        self.seqLen = len(subSequence)
        #self.scoreGenerator(subSequence,scoreRange)
        self.suffix = ''
       
    def addError(self,error,errorRate):
        candAlleles = ['A','C','G','T']
        errorProb = [random.uniform(0,1) for x in range(self.seqLen)]
        errorIndex = [errorProb.index(x) for x in errorProb if x <= errorRate]    
        for i in errorIndex:
            rawAllele = self.seq[i]
            newAllele = random.sample([x for x in candAlleles if x != rawAllele],1)[0]
            if rawAllele != newAllele:
                self.seq[i] = rawAllele
                error.addItem(self.refChr,self.refStart,self.startPosition,i,rawAllele,newAllele)
                self.score[i] = chr(random.sample(range(0,20),1)[0]+33)

    def scoreGenerator(self,scoreRange):
        scoreR = list(range(int(math.ceil(self.seqLen/2.0))))
        rawScore1 = [int(scoreRange[1] -  random.gammavariate(1,0.5) - x*random.normalvariate(0.1,0.03)) for x in scoreR]
        scoreR.reverse()
        if (self.seqLen/2.0)%1 != 0:
            scoreR = scoreR[:-1]
        rawScore2 = [int(scoreRange[1] -  random.gammavariate(1,0.5) - x*random.normalvariate(0.1,0.03)) for x in scoreR]
        self.score = [chr(x+33) for x in rawScore1 + rawScore2]
        #print self.seqLen,len(self.score)
        #self.read1Score = [chr(x+33) for x in rawScore1]
        #self.read2Score = [chr(x+33) for x in rawScore2]

    def addSNP(self, snp):
        for index in range(len(snp.snpBufferIndex)):
            p = random.uniform(0,1)
            if((snp.snpBufferIndex[index] >= self.startPosition \
                and snp.snpBufferIndex[index] < self.startPosition + self.read1Len) \
                or (snp.snpBufferIndex[index] >= self.startPosition + self.seqLen - self.read2Len \
                    and snp.snpBufferIndex[index] < self.startPosition + self.seqLen)):
                snp.totalReadsCount[index] = snp.totalReadsCount[index] + 1
                if(p <= snp.snpFraction[index]+0.01):
                    self.seq[snp.snpBufferIndex[index] - self.startPosition] = snp.snpAlleles[index] 
                    snp.addedCount[index] = snp.addedCount[index] + 1
                    self.suffix = self.suffix + '_' + str(snp.absolutePosition[index])
                              
    def addDeletion(self,dels):
        for index in range(len(dels.delBufferIndex)):
            p = random.uniform(0,1)
            if((dels.delBufferIndex[index]+dels.delLen[index] >= self.startPosition \
                and dels.delBufferIndex[index] < self.startPosition + self.read1Len) \
                    or (dels.delBufferIndex[index]+dels.delLen[index] >= self.startPosition + self.seqLen - self.read2Len \
                        and dels.delBufferIndex[index] < self.startPosition + self.seqLen)):
                dels.totalReadsCount[index] = dels.totalReadsCount[index] + 1
                if(p < dels.delFraction[index]+0.01):
                    delIndex = dels.delBufferIndex[index]-self.startPosition
                    if(delIndex <0):
                        self.seq[:delIndex+dels.delLen[index]] = '-'*(delIndex+dels.delLen[index])
                    else:
                        self.seq[delIndex:delIndex+dels.delLen[index]] = '-' * dels.delLen[index]
                    dels.addedCount[index] = dels.addedCount[index]+1
                    self.suffix = self.suffix + '_' + str(dels.absolutePosition[index])
        
    def addInsertion(self,ins):
        for index in range(len(ins.insBufferIndex)):
            p = random.uniform(0,1)
            if((ins.insBufferIndex[index] >= self.startPosition \
                and ins.insBufferIndex[index] < self.startPosition + self.read1Len) \
                    or (ins.insBufferIndex[index] >= self.startPosition + self.seqLen - self.read2Len \
                        and ins.insBufferIndex[index] < self.startPosition + self.seqLen)):
                ins.totalReadsCount[index] = ins.totalReadsCount[index] + 1
                if(p < ins.insFraction[index]+0.01):
                    insIndex = ins.insBufferIndex[index]-self.startPosition
                    if self.seq[insIndex] == '-':
                        print(self.seq)
                        print(ins.insBufferIndex[index],self.startPosition)
                        self.seq[insIndex] = str(self.seq[insIndex]) + ins.insAllele[index]
                    ins.addedCount[index] = ins.addedCount[index]+1
                    self.suffix = self.suffix + '_' + str(ins.absolutePosition[index])
    
    def pairedEndConverter(self):
        self.read1 = self.seq[:self.read1Len]
        baseComplement = {'A': 'T', 'C': 'G', 'T': 'A', 'G': 'C'}
        tmpRead2 = self.seq[-self.read2Len:]
        self.read2 = [baseComplement[x] for x in tmpRead2]
        self.read2.reverse()
        self.read1Score = self.score[:self.read1Len]
        self.read2Score = self.score[-self.read2Len:]
        self.read2Score.reverse()        

    def readsFinalizer(self,errorRate,error):
        index=0
        tmp = self.seq
        while index < len(self.seq):
           # print self.seq[index]
            if len(self.seq[index]) > 1:
                self.seq = self.seq[:index] + list(self.seq[index]) + self.seq[index+1:]
                index = index + len(self.seq[index])
            elif self.seq[index] != '-':
                index = index + 1
            else:
                self.seq.pop(index)
        self.seqLen = len(self.seq)
        self.scoreGenerator([0,40])
        if(errorRate > 0):
            self.addError(error,errorRate)
        self.pairedEndConverter()

    def writeToFile(self,readsFileHandle):
        readsFileHandle.reads1F.write(self.id + self.suffix + '/1\n')
        readsFileHandle.reads1F.write(''.join(self.read1) + '\n')
        readsFileHandle.reads1F.write('+' + '\n')
        readsFileHandle.reads1F.write(''.join(self.read1Score) + '\n')
        readsFileHandle.reads2F.write(self.id + self.suffix + '/2\n')
        readsFileHandle.reads2F.write(''.join(self.read2) + '\n')
        readsFileHandle.reads2F.write('+' + '\n')
        readsFileHandle.reads2F.write(''.join(self.read2Score) + '\n')
    
    def printer(self):
        print(self.id)
        print(self.seq)
        print(self.score)


# SNP are initilized before simulating reads.
# SNP information including real coverage, ref/alter alleles and locations are added by reads.addSNP().
# SNP information are written to file after simulation.
class SNP:
    def __init__(self,snpPercentage,sequence,absoluteStart,strand,recordID,snpFraction,bufferRegion,varIndexes):
        #random.seed(10) #delete later
        self.sequence = sequence[bufferRegion:-bufferRegion]
        self.snpCount = int(math.floor(len(self.sequence) * snpPercentage))
        self.snpIndex = sorted(random.sample(range(len(self.sequence)),self.snpCount))
        for index in self.snpIndex:
            if list(self.sequence[index-3:index+4]).count(self.sequence[index]) == 7 or index in varIndexes:
            # Avoid streth of alleles or positions already have Indels
                self.snpIndex.remove(index)
                self.snpCount -= 1
        self.snpBufferIndex = [x + bufferRegion for x in self.snpIndex]
        self.snpAlleles = self.findAllele(self.snpIndex,self.sequence)
        self.snpFraction = [snpFraction] * self.snpCount    
        self.addedCount = [0] * len(self.snpIndex)
        self.recordID = recordID
        self.strand = strand
        self.totalReadsCount = [0] * len(self.snpIndex)
        self.absolutePosition = [x + absoluteStart for x in self.snpBufferIndex]
 
    # Assign alternative alleles to pre-defined SNP
    def findAllele(self,snpIndex,sequence):
        snpAlleles = []
        candAlleles = ['A','C','G','T']
        for x in self.snpIndex:
            candAlleles.remove(sequence[x])
            snpAlleles = snpAlleles + random.sample(candAlleles,1)
            candAlleles = ['A','C','G','T']
        return snpAlleles
    
    def writeToFile(self,fileH):
        for i in range(len(self.addedCount)):
            fileH.write('\t'.join([self.recordID,str(self.absolutePosition[i]),self.sequence[self.snpIndex[i]],self.snpAlleles[i],str(self.addedCount[i]),str(self.totalReadsCount[i])])+'\n')

    def printer(self):
        print(self.snpIndex)
        print(self.snpAlleles)
        print(self.snpFraction)	

# Deletions are initilized before simulating reads.
# Deletion information including read coverage, ref/alter allele and 
# locations are added by reads.addDeletion().
# Deletion information are written to file after simulation.
class Deletion:
    def __init__(self,sequence,absoluteStart,strand,recordID,delFraction,bufferRegion,varIndexes):
        self.sequence = sequence[bufferRegion:-bufferRegion]
        self.delLen = []
        self.delIndex = []
        self.delAllele = []
        lenSet = [1]* 200 + [2]*40 + [5]*20 + [10]*10 + [15]*10 + [20]*5 + [30]*5 + [50]*2
        index = random.sample(range(50),1)[0]
        self.preAllele = []
        while index < len(self.sequence):
            curDelLen = random.sample(lenSet,1)[0]
            if curDelLen + index >= len(self.sequence):
                break
            if list(self.sequence[index:index+curDelLen]).count(self.sequence[index]) == curDelLen: 
                while sequence[index+bufferRegion-1] == sequence[index+bufferRegion]:
                    index -= 1
                if index < 0 or list(self.sequence[index:index+7]).count(self.sequence[index]) == 7:
                    break
            self.delLen.append(curDelLen)
            self.delAllele.append(self.sequence[index:index+curDelLen])
            self.preAllele.append(self.sequence[index-1])
            self.delIndex.append(index)
            varIndexes.extend(range(index,index+curDelLen))
            # Deletions are simulated with 150-350bp between each other
            index = index + random.sample(range(150,350),1)[0]
        self.delCount = len(self.delLen)
        self.delFraction = [delFraction] * self.delCount
        self.delBufferIndex = [x + bufferRegion for x in self.delIndex]
        self.addedCount = [0] * len(self.delIndex)
        self.recordID = recordID
        self.strand = strand
        self.totalReadsCount = [0] * len(self.delIndex)
        self.absolutePosition = [x + absoluteStart-1 for x in self.delBufferIndex]
    
    def writeToFile(self,fileH):
        for i in range(len(self.addedCount)):
            fileH.write('\t'.join([self.recordID,str(self.absolutePosition[i]-1),self.preAllele[i],str(self.preAllele[i])+'-'*self.delLen[i],str(self.addedCount[i]),str(self.totalReadsCount[i])])+'\n')

    def printer(self):
        print(self.delIndex)
        print(self.delAllele)
        print(self.delFraction)	


# Insertions are initilized before simulating reads.
# Insertion information including locations, coverage by reads and ref/alter 
# alleles are added by reads.addInsertion().
# Insertion information are written to file after simulation.
class Insertion:
    def __init__(self,sequence,absoluteStart,strand,recordID,insFraction,bufferRegion,varIndexes):
        #print varIndexes
        self.sequence = sequence[bufferRegion:-bufferRegion]
        self.insLen = []
        self.insIndex = []
        self.insAllele = []
        lenSet = [1]* 200 + [2]*40 + [5]*20 + [10]*10 + [15]*10 + [20]*5 + [30]*5 + [50]*2
        index = random.sample(range(50),1)[0]
        self.currentAllele = []
        while index < len(self.sequence):
            #while index in varIndexes:
            #    index = index + random.sample(range(50,100),1)[0]
            if index >= len(self.sequence):
                break
            while sequence[index+bufferRegion] == sequence[index+bufferRegion-1]:
                index -= 1
            if index < 0 or list(self.sequence[index:index+7]).count(self.sequence[index]) == 7 or index in varIndexes:
                break
            curInsLen = random.sample(lenSet,1)[0]
            inAllele =''.join([random.sample(['A','T','C','G'],1)[0] for x in range(curInsLen)])
            self.insLen.append(curInsLen)
            self.insAllele.append(inAllele)
            self.currentAllele.append(self.sequence[index])
            self.insIndex.append(index)
            varIndexes.append(index)
            # Insetions are simulated with 150-350 bp between each other.
            index = index + random.sample(range(150,350),1)[0]
        self.insCount = len(self.insLen)
        self.insFraction = [insFraction] * self.insCount
        self.insBufferIndex = [x + bufferRegion for x in self.insIndex]
        self.addedCount = [0] * len(self.insIndex)
        self.recordID = recordID
        self.strand = strand
        self.totalReadsCount = [0] * len(self.insIndex)
        self.absolutePosition = [x + absoluteStart for x in self.insBufferIndex]

    def writeToFile(self,fileH):
        for i in range(len(self.addedCount)):
            fileH.write('\t'.join([self.recordID,str(self.absolutePosition[i]),self.currentAllele[i],self.currentAllele[i]+self.insAllele[i],str(self.addedCount[i]),str(self.totalReadsCount[i])])+'\n')

    def printer(self):
        print(self.insIndex)
        print(self.insAllele)
        print(self.insFraction)	

   
class Error:
    def __init__(self):
        self.errorInfor = {}

    def addItem(self,refChr,refStart,parentIndex,localIndex,rawAllele,newAllele):
        globalIndex = str(refStart + parentIndex + localIndex)
        key=refChr + ':' + globalIndex
        #print(key, rawAllele, newAllele)
        if key not in self.errorInfor:
            self.errorInfor[key] = [refChr,globalIndex,rawAllele,newAllele]
        else:
            self.errorInfor[key][3] = self.errorInfor[key][3] + '\\' + newAllele    

    def writeToFile(self,fileH):
        for key in self.errorInfor:
            fileH.write('\t'.join(self.errorInfor[key])+'\n')


class ReadsFileHandle:
    def __init__(self,filePrefix,varOutFile,errorOutFile):
        self.fileName = [filePrefix+'1.fastq',filePrefix+'2.fastq']
        self.varOutFile = varOutFile
        self.errorOutFile = errorOutFile

    def fileOpen(self):
        self.errorFH = open(self.errorOutFile,'w')
        self.varFH = open(self.varOutFile,'w')
        self.reads1F = open(self.fileName[0],'a')
        self.reads2F = open(self.fileName[1],'a')
            
    def fileClose(self):
        self.errorFH.close()
        self.varFH.close()
        self.reads1F.close()
        self.reads2F.close()
    
    def fileDelete(self):
        for file in self.fileName:
            if os.path.isfile(file):
                print('Removing ' + str(file) + '!')
                os.system('rm ' + file)
        if os.path.isfile(self.varOutFile):
            print('Removing ' + self.varOutFile + '!')
            os.system('rm ' + self.varOutFile)

        if os.path.isfile(self.errorOutFile):
            print('Removing ' + self.errorOutFile + '!')
            os.system('rm ' + self.errorOutFile)


# Function for generating reads
def generateReads(seqBiopython,readsFileH,parameters):
    sequence = seqBiopython.seq
    # id format such as chr13:32,908,718-32,916,660 is expected
    idPrefix = seqBiopython.id.split(':')

    chrId = idPrefix[0]
    startBp = int(idPrefix[1].split('-')[0].replace(',',''))

    strand = '+'
    #readLen = parameters['readLen']
    varIndexes = []
    bufferRegion = parameters['bufferRegion']
    if parameters['del']:
        dels = Deletion(sequence,startBp,strand,chrId,parameters['varFraction'],bufferRegion,varIndexes)
    if parameters['ins']:
        ins = Insertion(sequence,startBp,strand,chrId,parameters['varFraction'],bufferRegion,varIndexes)
    if parameters['snp']:
        snp = SNP(parameters['snpPercentage'],sequence,startBp,strand,chrId,parameters['varFraction'],bufferRegion,varIndexes)
    error = Error()
    seqLen =len(sequence)
#    for i in range(seqLen - min(readLen,read1Len+read2Len)):
    for i in range(0,seqLen-bufferRegion):
        read1Len = parameters['read1Len']
        read2Len = parameters['read2Len']
        multiple = parameters['coverage']/float(read1Len+read2Len)
        while(multiple > 0):
            p = random.uniform(0,1)
            if(p <= multiple):
                idPrefixSuffix = seqBiopython.id + '_' + str(multiple)            
	        #dynamicGap = random.sample(range(min(readLen,seqLen - i)-read1Len-read2Len),1)[0]
                read = Read(i,sequence,idPrefixSuffix,read1Len,read2Len,chrId,startBp)
                if parameters['del']:
                    read.addDeletion(dels)
                if parameters['ins']:
                    read.addInsertion(ins)
                if parameters['snp']:
                    read.addSNP(snp)
                try:
                    read.readsFinalizer(parameters['errorRate'],error)
                except:
                    print(ins.insIndex,ins.insLen)
                    print(dels.delIndex,dels.delLen)
                    print(varIndexes)
                read.writeToFile(readsFileH)
            multiple = multiple-1
    if parameters['snp']:
        snp.writeToFile(readsFileH.varFH) 
    if parameters['del']:
        dels.writeToFile(readsFileH.varFH)
    if parameters['ins']:
        ins.writeToFile(readsFileH.varFH)
    error.writeToFile(readsFileH.errorFH)

def argumentParser(argv):
    try:
        opts, args = getopt.getopt(argv,'hG:S:F:E:12',
            ['help','coverage=','readsOutFile=','errorRate=','readLength=','varFraction=','scoreRange=',\
            'bufferRegion=','snpPercentage=','varOutFile=','refGenome=','readsOutFile=','errorOutFile=',\
            'snp','deletion','insertion'])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    
    parameters = {'refGenome' : '',
        'varOutFile' : '',
        'errorOutFile' : '',
        'readsOutFilePrefix' : '',
        'coverage' : 50,
        'errorRate' : 0.01,
        'readLen' : 400,
        'snpPercentage' : 0.01,
        'varFraction' : 0.5,
        'scoreRange' : [0,40],
        'bufferRegion' : 100,
        'read1Len' : 150,
        'read2Len' : 150,
        'snp' : False,
        'del' : False,
        'ins' : False,
        'seed': None
    }
	
    for opt,arg in opts:
        if opt in ('-h','--help'):
            usage()
            sys.exit()
        elif opt in ('-G','--refGenome'):
            parameters['refGenome'] = arg
        elif opt in ('-S','--varOutFile'):
            parameters['varOutFile'] = arg
        elif opt in ('-F','--readsOutFile'):
            parameters['readsOutFilePrefix'] = arg
        elif opt in ('-E','--errorOutFile'):
            parameters['errorOutFile'] = arg
        elif opt == '--errorRate':
            parameters['errorRate'] = float(arg)
        elif opt == '--readLength':
            parameters['readLen'] = int(arg)
        elif opt == '--varFraction':
            parameters['varFraction'] = float(arg)
        elif opt == '--scoreRange':
            parameters['scoreRange'] = arg
        elif opt == '--bufferRegion':
            parameters['bufferRegion'] = int(arg)
        elif opt == '--snpPercentage':
            parameters['snpPercentage'] = float(arg)
        elif opt == '--coverage':
            parameters['coverage'] = int(arg)
        elif opt == '-1':
            parameters['read1Len'] = int(arg)
        elif opt == '-2':
            parameters['read2Len'] = int(arg)
        elif opt == '--snp':
            parameters['snp'] = True
        elif opt == '--deletion':
            parameters['del'] = True
        elif opt == '--insertion':
            parameters['ins'] = True
        elif opt == '--seed':
            parameters['seed'] = int(arg)
        else:
            assert False, 'unhandeld option'
    
    return parameters
			
def usage():
    print("Usage:")
    

def main():
    para = argumentParser(sys.argv[1:])
    if para['seed'] is not None:
        random.seed(para['seed'])
    readsFileH = ReadsFileHandle(para['readsOutFilePrefix'],para['varOutFile'],para['errorOutFile'])
    readsFileH.fileDelete()
    readsFileH.fileOpen()
    print('Start simulating.')
    for seqRecord in SeqIO.parse(para['refGenome'],'fasta'):
        generateReads(seqRecord,readsFileH,para)
    readsFileH.fileClose()

if __name__ == "__main__":
    main()
