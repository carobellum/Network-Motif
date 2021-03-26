#!/usr/bin/env python
# encoding: utf-8
"""
FinalMotif.py

Created by BNIAC on 2012-08-02.
"""

import sys
import os
import random as rd
import math
import heapq
import json
import _pickle as cPickle
import networkx as nx
import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
import operator
import csv
import itertools
from scipy.sparse import dok_matrix
from itertools import izip
from itertools import repeat
from collections import defaultdict
GRAPHSIZE = 88


class MotifData:
    "Class containing motif data for a set of graphs"

    def __init__(self, data):
        self.subgraphs,
        self.data = zip(*data)
        allkeys = set()
        for dic in self.data:
            allkeys.update(set(dic.keys()))
        self.keys = allkeys

    def __getitem__(self, motif):
        "Get array of number of motif for each patient"
        motif = unicode(motif)
        row = [d[motif] if motif in d else 0. for d in self.data]
        return np.array(row)

    def __contains__(self, item):
        return self.keys.__contains__(unicode(item))

    def __iter__(self):
        return iter(self.data)

    def __len__(self):
        return len(self.data)

    def iterSortedValues(self):
        "Iterate sorted motif values for each patient"
        return (sorted(g.values()) for g in iter(self.data))

    def topMotifs(self, num):
        "Return top num motifs"
        return heapq.nlargest(num, self.keys, key=lambda x: self[x].mean())

    def iterTotals(self):
        "Iterate through total number of motifs for each patient"
        for d, sub in izip(self.data, self.subgraphs):
            t = {}
            for motif, value in d.iteritems():
                t[int(i)] = int(value * sub + 0.1)
            yield t

    def getPatient(self, pat):
        return self.data[pat]

    def getSubgraphs(self, pat):
        return self.subgraphs[pat]


# do a permutation "t-test" of significance of the two means
def permttest(d1, d2, kmax=5000):  # d is vector with 2 groups of data, maxk = max shuffles
    sign = d1.mean() - d2.mean()
    d1 = list(d1)
    d2 = list(d2)
    nd1, nd2 = d1, d2
    n1, n2 = len(d1), len(d2)
    n = n1 + n2
    dtot = d1 + d2
    mvreal = 1.0 * sum(d1) / n1 - 1.0 * sum(d2) / n2
    mvs = []
    # shuffle and compute
    for k in range(kmax):
        rd.shuffle(dtot)
        nd1 = dtot[0:n1]
        nd2 = dtot[n1:n]
        mvs += [1.0 * sum(nd1) / n1 - 1.0 * sum(nd2) / n2]
    mvs = sorted(mvs)
    for i in range(kmax):
        if mvreal < mvs[i]:
            return (sign, (min(1.0 * (kmax - i) / kmax, 1.0 * i / kmax)))
    return (sign, (1.0 / kmax))


def makeSwapData(degree=10):
    """generates edgeswapped graph pickle file"""
    with open("aznorbert_corrsd_new.pkl", "rb") as f:
        data = pickle.load(f)

    swapData = {}

    for key, graphs in data.iteritems():
        print("Current Group: " + str(key))
        keyData = []
        for i, G in enumerate(graphs):
            print("Edge-Swapping Graph:", i)
            sortedWeights = np.sort(G, axis=None)
            threshold = sortedWeights[-len(G) * degree - 1]

            graph = nx.DiGraph(G > threshold)
            diff = randomize_graph(graph, 2500)
            keyData.append(graph)
        swapData[key] = keyData

    with open("SwapData" + str(degree) + ".pkl", 'wb') as f:
        pickle.dump(swapData, f)


def buildCache(motifSize, degree):
    """builds cache for graphs (both edge-swapped and original)"""
    with open("aznorbert_corrsd_new.pkl", "rb") as f:
        data = pickle.load(f)

    with open("SwapData" + str(degree) + ".pkl", "rb") as pic:
        randGraphs = pickle.load(pic)

    for corr in ("corr", "lcorr", "lacorr"):
        for ty in ("AD", "MCI", "NL", "CONVERT"):
            print("Building Cache for " + str((corr, ty)))
            findMotifs(data, (ty, corr), motifSize, degree, randGraphs)
            findMotifs(data, (ty, corr), motifSize, degree)


def findMotifs(data, key, motifSize=3, degree=10, randGraphs=None, useCache=True, printMotifs=False):

    def printMotifs(motifs, filename):
        """writes motifs to file by descending frequency"""
        tempmotifdict = defaultdict(float)
        numpatients = float(len(motifs))
        for patient, motifdict in motifs:
            for motif, freq in motifdict.items():
                #		 print(motif, freq)
                tempmotifdict[motif] += freq / numpatients

        motiflist = sorted(tempmotifdict.iteritems(),
                           key=operator.itemgetter(1), reverse=True)
        f = open(filename, 'wb')
        f.write('Motifs:	 Frequencies:\n')
        for motif, freq in motiflist:
            f.write(str(motif).ljust(12) + "%.2f" % (freq * 100) + '%' + '\n')
        f.close()

    """Main finding motifs routine"""
    if key == "rand":
        """Generate random adjacency matricies"""
        graphs = []
        for i in xrange(100):
            x = np.random.rand(GRAPHSIZE, GRAPHSIZE)
            x -= np.diag(np.diag(x))
            graphs.append(x)
    else:
        graphs = data[key]

    # Check cache
    filename = "" if randGraphs is None else "RAND"
    filename += str(key) + 's' + str(int(motifSize)) + \
        'd' + str(int(degree)) + ".json"
    if os.path.exists('cache/' + filename) and useCache:
        print("in cache")
        cachedata = json.load(open('cache/' + filename, "rb"))
        if printMotifs:
            frequency_filename = "MotifFrequencyDegree{}/{}.txt".format(
                degree, filename[:-5])
            printMotifs(cachedata, frequency_filename)

        return MotifData(cachedata)

    motifs = []
    numstring = "/" + str(len(graphs))
    rejected = 0
    for index, G in enumerate(graphs):
        # Cull bad graphs
        if np.count_nonzero(G) < len(G) * degree:
            rejected += 1
            continue

        # calculate threshold
        sortedWeights = np.sort(G, axis=None)
        threshold = sortedWeights[-len(G) * degree - 1]
        # print(progress)
        sys.stdout.write("\rMotif Finding Progress: " + str(index) + numstring)
        sys.stdout.write(" Threshold: " + str(threshold) + '\n')
        sys.stdout.flush()

        # Output graph to txt file
        graph = nx.DiGraph(G > threshold)
        graph = nx.convert_node_labels_to_integers(graph, 1)
        if randGraphs is not None:
            graph = randGraphs[key][index]
        with open('result/OUTPUT.txt', 'wb') as f:
            f.write(str(len(graph)) + '\n')
            nx.write_edgelist(graph, f, data=False)

        # Jenky way to use c++ motif finder in python
        os.system("./Kavosh " + str(motifSize))
        with open("result/MotifCount.txt", "rb") as f:
            subgraphs = float(f.next())
            data = np.loadtxt(f, ndmin=2)

        # Append data for this graph
        personMotifs = {}
        for iD, total in data:
            personMotifs[unicode(int(iD))] = total / subgraphs
        motifs.append((int(subgraphs), personMotifs))

    print('\nMotifs Done! Graphs Rejected: ' + str(rejected))

    # add motifs to cache

    # if printMotifs:
    #	print(motifs)

    if useCache:
        if not os.path.isdir('cache'):
            os.makedirs('cache')
        json.dump(motifs, open('cache/' + filename, 'wb'),
                  separators=(',', ':'))

    if printMotifs:
        frequency_filename = "MotifFrequencyDegree{}/{}.txt".format(
            degree, filename[:-5])
        printMotifs(motifs, frequency_filename)

    return MotifData(motifs)


def convertIDToGraph(mid, motifSize, save=False):
    """Draw graph with id and motifSize"""
    binary = bin(mid)
    adj = np.zeros(motifSize * motifSize)
    l = 0
    for x in xrange(1, motifSize * motifSize + 1):
        if binary[-x + l] == 'b':
            break
        if (x - 1) % (motifSize + 1) == 0:
            l += 1
        else:
            adj[-x] = int(binary[-x + l])
    adj.shape = (motifSize, motifSize)
    graph = nx.to_networkx_graph(adj, create_using=nx.DiGraph())
    nx.draw_circular(graph)
    if save:
        plt.savefig("result/id-" + str(id) + "size-" + str(motifSize))
    else:
        plt.show()
    plt.clf()


def plotMotifGraphs(data, motifSize=3, degree=10, numofmotifs=10, usetotal=False):
    """Draws graph compairing average motif count between samples in the data"""
    for corr in ('corr', 'lcorr', 'lacorr'):

        nl = findMotifs(data, ('NL', corr), motifSize, degree)
        mci = findMotifs(data, ('MCI', corr), motifSize, degree)
        ad = findMotifs(data, ('AD', corr), motifSize, degree)
        convert = findMotifs(data, ('CONVERT', corr), motifSize, degree)

        keys = nl.topMotifs(numofmotifs)

        meansNL = []
        meansMCI = []
        meansAD = []
        meansCONVERT = []
        stdNL = []
        stdMCI = []
        stdAD = []
        stdCONVERT = []
        for key in keys:
            meansNL.append(nl[key].mean() if key in nl else 0.)
            stdNL.append(nl[key].std() if key in nl else 0.)
            meansMCI.append(mci[key].mean() if key in mci else 0.)
            stdMCI.append(mci[key].std() if key in mci else 0.)
            meansAD.append(ad[key].mean() if key in mci else 0.)
            stdAD.append(ad[key].std() if key in mci else 0.)
            meansCONVERT.append(convert[key].mean() if key in convert else 0.)
            stdCONVERT.append(convert[key].std() if key in convert else 0.)

        ind = np.arange(numofmotifs)
        width = 0.2

        NLplt = plt.bar(ind, meansNL, width, color='b', yerr=stdNL, ecolor='y')
        MCIplt = plt.bar(ind + width, meansMCI, width,
                         color='y', yerr=stdMCI, ecolor='b')
        ADplt = plt.bar(ind + width + width, meansAD, width,
                        color='g', yerr=stdAD, ecolor='r')
        CONVERTplt = plt.bar(ind + width + width + width, meansCONVERT,
                             width, color='r', yerr=stdCONVERT, ecolor='y')

        plt.ylabel('Average number of motifs')
        plt.xlabel('Motif ID')
        plt.title('Motif size ' + str(motifSize) + ' distribution for ' +
                  corr + " with average degree " + str(degree))
        plt.xticks(ind + width + width / 2., keys)
        plt.ylim(ymin=0.0)
        plt.legend((NLplt[0], MCIplt[0], ADplt[0],
                    CONVERTplt[0]), ('NL', 'MCI', 'AD', 'CONVERT'))
        plt.grid(True)
        header = 'result/MotifDistribution-'
        plt.savefig(header + corr + "_D-" +
                    str(degree) + "_S-" + str(motifSize))
        plt.clf()


def PDFstats(data, filename, edgeSwap=False, motifSize=3, degree=10):
    """Output a latex pdf of motif stats"""
    filename = "result/" + filename + ".tex"

    if not edgeSwap:
        motifsNLRAND = motifsMCIRAND = motifsADRAND = motifsCONVERTRAND = findMotifs(
            data, "rand", motifSize=motifSize, degree=degree)

    with open(filename, 'wb') as f:
        f.write(
            "\\documentclass{article}\n"
            "\\usepackage{amsmath,fullpage,graphicx,fancyhdr,xcolor,colortbl,chngpage}\n"
            "\\usepackage[landscape]{geometry}"
            "\\definecolor{yellow}{RGB}{255,255,70}\n"
            "\\definecolor{orange}{RGB}{255,165,70}\n"
            "\\definecolor{red}{RGB}{255,70,70}\n"
            "\\title{Motif Data}\n"
            "\\author{Graham Tremper}\n"
            "\\date{}\n"
            "\\fancyhead{}\n"
            "\\begin{document}\n"
        )

        if edgeSwap:
            with open("SwapData" + str(degree) + ".pkl", "rb") as pic:
                randGraphs = pickle.load(pic)

        statistics = {}
        for corr in ('corr', 'lcorr'):
            print("Starting " + corr + "...")
            motifsNL = findMotifs(data, ('NL', corr),
                                  motifSize=motifSize, degree=degree)
            motifsMCI = findMotifs(data, ('MCI', corr),
                                   motifSize=motifSize, degree=degree)
            motifsAD = findMotifs(data, ('AD', corr),
                                  motifSize=motifSize, degree=degree)
            motifsCONVERT = findMotifs(
                data, ('CONVERT', corr), motifSize=motifSize, degree=degree)
            if edgeSwap:
                motifsNLRAND = findMotifs(
                    data, ('NL', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsMCIRAND = findMotifs(
                    data, ('MCI', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsADRAND = findMotifs(
                    data, ('AD', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsCONVERTRAND = findMotifs(
                    data, ('CONVERT', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)

            allMotifs = list(motifsNL.keys
                             & motifsAD.keys
                             & motifsMCI.keys
                             & motifsCONVERT.keys
                             & motifsNLRAND.keys
                             & motifsMCIRAND.keys
                             & motifsADRAND.keys
                             & motifsCONVERTRAND.keys)

            allMotifs = motifsNL.topMotifs(30)

            motifStats = []
            for key in allMotifs:
                norm = motifsNL[key]
                mci = motifsMCI[key]
                ad = motifsAD[key]
                conv = motifsCONVERT[key]
                c1 = permttest(norm, mci)
                c2 = permttest(norm, ad)
                c3 = permttest(norm, conv)
                c4 = permttest(mci, ad)
                c5 = permttest(mci, conv)
                c6 = permttest(ad, conv)
                c7 = permttest(norm, motifsNLRAND[key])
                c8 = permttest(mci, motifsMCIRAND[key])
                c9 = permttest(ad, motifsADRAND[key])
                c10 = permttest(conv, motifsCONVERTRAND[key])
                motifStats.append(
                    (key, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10))

            f.write(
                "\\begin{table}[t]\n"
                "\\begin{adjustwidth}{-1.5in}{-1.5in} "
                "\\caption{Motif T-test results from " +
                corr + " data with using edge swap}\n"
                "\\centering\n"
                "\\begin{tabular}{|c|c|c|c|c|c|c|c|c|c|c|}\n"
                "\\hline\n"
                "\\rowcolor[gray]{0.85}\n"
                "Key & NL to MCI & NL to AD & NL to Conv & MCI to AD & MCI to Conv & AD to Conv & NL to Rand & MCI to Rand & AD to Rand & Conv to Rand \\\\ \\hline\n"
            )
            for stat in motifStats:
                f.write(str(stat[0]) + " \\cellcolor[gray]{0.95}")
                for sign, col in stat[1:]:
                    cell = " & {0:.3}".format(col)
                    if sign > 0:
                        cell += '(+)'
                    else:
                        cell += '(-)'

                    if col <= 0.01:
                        cell += " \\cellcolor{red} "
                    elif col <= 0.05:
                        cell += " \\cellcolor{orange}"
                    elif col <= 0.1:
                        cell += " \\cellcolor{yellow}"
                    f.write(cell)
                f.write("\\\\ \\hline\n")

            f.write(
                "\\end{tabular}\n"
                "\\end{adjustwidth}"
                "\\end{table}\n"
            )

        f.write("\\end{document}\n")

    os.system("pdflatex -output-directory result " + filename)
    os.system("rm result/*.log result/*.aux")


def createfakeGroups(data, motifSize):
    "Create new random groups by proportionally shuffling all the groups together"
    newdata = {}
    for corr in ('corr', 'lcorr', 'lacorr'):
        newdata[('NL', corr)] = []
        newdata[('AD', corr)] = []
        newdata[('MCI', corr)] = []
        newdata[('CONVERT', corr)] = []

        nlData = list(findMotifs(data, ('NL', corr), motifSize=motifSize).data)
        adData = list(findMotifs(data, ('AD', corr), motifSize=motifSize).data)
        mciData = list(findMotifs(
            data, ('MCI', corr), motifSize=motifSize).data)
        convertData = list(findMotifs(
            data, ('CONVERT', corr), motifSize=motifSize).data)

        adlen = len(adData)
        nllen = len(nlData)
        mcilen = len(mciData)
        convertlen = len(convertData)
        total = adlen + nllen + mcilen + convertlen

        myList = [nllen, adlen, mcilen, convertlen]
        for i in xrange(4):
            n = int(float(myList[i]) / float(total) * nllen)
            for j in xrange(n):
                if i == 0:
                    g = nlData.pop(rd.randrange(len(nlData)))
                    newdata[('NL', corr)].append(g)
                if i == 1:
                    g = adData.pop(rd.randrange(len(adData)))
                    newdata[('NL', corr)].append(g)
                if i == 2:
                    g = mciData.pop(rd.randrange(len(mciData)))
                    newdata[('NL', corr)].append(g)
                if i == 3:
                    g = convertData.pop(rd.randrange(len(convertData)))
                    newdata[('NL', corr)].append(g)

        for i in xrange(4):
            n = int(float(myList[i]) / float(total) * adlen)
            for j in xrange(n):
                if i == 0:
                    g = nlData.pop(rd.randrange(len(nlData)))
                    newdata[('AD', corr)].append(g)
                if i == 1:
                    g = adData.pop(rd.randrange(len(adData)))
                    newdata[('AD', corr)].append(g)
                if i == 2:
                    g = mciData.pop(rd.randrange(len(mciData)))
                    newdata[('AD', corr)].append(g)
                if i == 3:
                    g = convertData.pop(rd.randrange(len(convertData)))
                    newdata[('AD', corr)].append(g)

        for i in xrange(4):
            n = int(float(myList[i]) / float(total) * mcilen)
            for j in xrange(n):
                if i == 0:
                    g = nlData.pop(rd.randrange(len(nlData)))
                    newdata[('MCI', corr)].append(g)
                if i == 1:
                    g = adData.pop(rd.randrange(len(adData)))
                    newdata[('MCI', corr)].append(g)
                if i == 2:
                    g = mciData.pop(rd.randrange(len(mciData)))
                    newdata[('MCI', corr)].append(g)
                if i == 3:
                    g = convertData.pop(rd.randrange(len(convertData)))
                    newdata[('MCI', corr)].append(g)

        for i in xrange(4):
            n = int(float(myList[i]) / float(total) * convertlen)
            for j in xrange(n):
                if i == 0:
                    g = nlData.pop(rd.randrange(len(nlData)))
                    newdata[('CONVERT', corr)].append(g)
                if i == 1:
                    g = adData.pop(rd.randrange(len(adData)))
                    newdata[('CONVERT', corr)].append(g)
                if i == 2:
                    g = mciData.pop(rd.randrange(len(mciData)))
                    newdata[('CONVERT', corr)].append(g)
                if i == 3:
                    g = convertData.pop(rd.randrange(len(convertData)))
                    newdata[('CONVERT', corr)].append(g)

        leftovers = nlData + adData + mciData + convertData
        while len(newdata['NL', corr]) < nllen:
            g = leftovers.pop(rd.randrange(len(leftovers)))
            newdata[('NL', corr)].append(g)

        while len(newdata['AD', corr]) < adlen:
            g = leftovers.pop(rd.randrange(len(leftovers)))
            newdata[('AD', corr)].append(g)

        while len(newdata['MCI', corr]) < mcilen:
            g = leftovers.pop(rd.randrange(len(leftovers)))
            newdata[('MCI', corr)].append(g)

        while len(newdata['CONVERT', corr]) < convertlen:
            g = leftovers.pop(rd.randrange(len(leftovers)))
            newdata[('CONVERT', corr)].append(g)

    return newdata


def PDFstatsShuf(data, filename, motifSize=3, degree=10):
    """Output a latex pdf of motif stats with the patient groups shuffled"""
    filename = "result/" + filename + ".tex"
    shufData = createfakeGroups(data, motifSize=motifSize)

    with open(filename, 'wb') as f:
        f.write(
            "\\documentclass{article}\n"
            "\\usepackage{amsmath,fullpage,graphicx,fancyhdr,xcolor,colortbl,chngpage}\n"
            "\\usepackage[landscape]{geometry}"
            "\\definecolor{yellow}{RGB}{255,255,70}\n"
            "\\definecolor{orange}{RGB}{255,165,70}\n"
            "\\definecolor{red}{RGB}{255,70,70}\n"
            "\\title{Motif Data}\n"
            "\\author{Graham Tremper}\n"
            "\\date{}\n"
            "\\fancyhead{}\n"
            "\\begin{document}\n"
        )

        statistics = {}
        for corr in ('corr', 'lcorr', 'lacorr'):
            print("Starting " + corr + "...")
            motifsNL = findMotifs(data, ('NL', corr),
                                  motifSize=motifSize, degree=degree)
            motifsMCI = findMotifs(data, ('MCI', corr),
                                   motifSize=motifSize, degree=degree)
            motifsAD = findMotifs(data, ('AD', corr),
                                  motifSize=motifSize, degree=degree)
            motifsCONVERT = findMotifs(
                data, ('CONVERT', corr), motifSize=motifSize, degree=degree)

            motifsNLRAND = shufData[('NL', corr)]
            motifsMCIRAND = shufData[('MCI', corr)]
            motifsADRAND = shufData[('AD', corr)]
            motifsCONVERTRAND = shufData[('CONVERT', corr)]

            NLRANDkeys = set()
            for dic in motifsNLRAND:
                NLRANDkeys.update(set(dic.keys()))

            MCIRANDkeys = set()
            for dic in motifsMCIRAND:
                MCIRANDkeys.update(set(dic.keys()))

            ADRANDkeys = set()
            for dic in motifsADRAND:
                ADRANDkeys.update(set(dic.keys()))

            CONVERTRANDkeys = set()
            for dic in motifsCONVERTRAND:
                CONVERTRANDkeys.update(set(dic.keys()))

            allMotifs = list(motifsNL.keys
                             & motifsAD.keys
                             & motifsMCI.keys
                             & motifsCONVERT.keys
                             & NLRANDkeys
                             & MCIRANDkeys
                             & ADRANDkeys
                             & CONVERTRANDkeys)

            allMotifs = motifsNL.topMotifs(30)

            motifStats = []
            for key in allMotifs:
                norm = motifsNL[key]
                mci = motifsMCI[key]
                ad = motifsAD[key]
                conv = motifsCONVERT[key]
                c1 = permttest(norm, mci)
                c2 = permttest(norm, ad)
                c3 = permttest(norm, conv)
                c4 = permttest(mci, ad)
                c5 = permttest(mci, conv)
                c6 = permttest(ad, conv)
                c7 = permttest(norm, np.array(
                    [d[key] if key in d else 0. for d in motifsNLRAND]))
                c8 = permttest(mci, np.array(
                    [d[key] if key in d else 0. for d in motifsMCIRAND]))
                c9 = permttest(ad, np.array(
                    [d[key] if key in d else 0. for d in motifsADRAND]))
                c10 = permttest(conv, np.array(
                    [d[key] if key in d else 0. for d in motifsCONVERTRAND]))
                motifStats.append(
                    (key, c1, c2, c3, c4, c5, c6, c7, c8, c9, c10))

            motifStats.sort(key=lambda x: motifsNL[x[0]].mean(), reverse=True)

            f.write(
                "\\begin{table}[t]\n"
                "\\begin{adjustwidth}{-1.5in}{-1.5in} "
                "\\caption{Motif T-test results from " +
                corr + " data with using edge swap}\n"
                "\\centering\n"
                "\\begin{tabular}{|c|c|c|c|c|c|c|c|c|c|c|}\n"
                "\\hline\n"
                "\\rowcolor[gray]{0.85}\n"
                "Key & NL to MCI & NL to AD & NL to Conv & MCI to AD & MCI to Conv & AD to Conv & NL to Rand & MCI to Rand & AD to Rand & Conv to Rand \\\\ \\hline\n"
            )
            for stat in motifStats:
                f.write(str(stat[0]) + " \\cellcolor[gray]{0.95}")
                for sign, col in stat[1:]:
                    cell = " & {0:.3}".format(col)
                    if sign > 0:
                        cell += '(+)'
                    else:
                        cell += '(-)'

                    if col <= 0.01:
                        cell += " \\cellcolor{red} "
                    elif col <= 0.05:
                        cell += " \\cellcolor{orange}"
                    elif col <= 0.1:
                        cell += " \\cellcolor{yellow}"
                    f.write(cell)
                f.write("\\\\ \\hline\n")

            f.write(
                "\\end{tabular}\n"
                "\\end{adjustwidth}"
                "\\end{table}\n"
            )

        f.write("\\end{document}\n")

    os.system("pdflatex -output-directory result " + filename)
    os.system("rm result/*.log result/*.aux")


def PDFdiststats(data, filename, edgeSwap=False, motifSize=3, degree=10):
    """Output a latex pdf of motif distribution (entrophy, gini coeff, fatness) stats"""
    filename = "result/" + filename + ".tex"

    if not edgeSwap:
        motifsNLRAND = motifsMCIRAND = motifsADRAND = motifsCONVERTRAND = findMotifs(
            data, "rand", motifSize=motifSize, degree=degree)

    with open(filename, 'wb') as f:
        f.write(
            "\\documentclass{article}\n"
            "\\usepackage{amsmath,fullpage,graphicx,fancyhdr,xcolor,colortbl,chngpage}\n"
            "\\usepackage[landscape]{geometry}"
            "\\definecolor{yellow}{RGB}{255,255,70}\n"
            "\\definecolor{orange}{RGB}{255,165,70}\n"
            "\\definecolor{red}{RGB}{255,70,70}\n"
            "\\title{Motif Data}\n"
            "\\author{Graham Tremper}\n"
            "\\date{}\n"
            "\\fancyhead{}\n"
            "\\begin{document}\n"
        )

        if edgeSwap:
            with open("SwapData" + str(degree) + ".pkl", "rb") as pic:
                randGraphs = pickle.load(pic)

        statistics = {}
        for corr in ('corr', 'lcorr', 'lacorr'):
            print("Starting " + corr + "...")
            motifsNL = findMotifs(data, ('NL', corr),
                                  motifSize=motifSize, degree=degree)
            NLd = diststats(motifsNL)
            motifsMCI = findMotifs(data, ('MCI', corr),
                                   motifSize=motifSize, degree=degree)
            MCId = diststats(motifsMCI)
            motifsAD = findMotifs(data, ('AD', corr),
                                  motifSize=motifSize, degree=degree)
            ADd = diststats(motifsAD)
            motifsCONVERT = findMotifs(
                data, ('CONVERT', corr), motifSize=motifSize, degree=degree)
            CONVERTd = diststats(motifsCONVERT)
            if edgeSwap:
                motifsNLRAND = findMotifs(
                    data, ('NL', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsMCIRAND = findMotifs(
                    data, ('MCI', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsADRAND = findMotifs(
                    data, ('AD', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)
                motifsCONVERTRAND = findMotifs(
                    data, ('CONVERT', corr), motifSize=motifSize, degree=degree, randGraphs=randGraphs)

            ADRANDd = diststats(motifsADRAND)
            MCIRANDd = diststats(motifsMCIRAND)
            CONVERTRANDd = diststats(motifsCONVERTRAND)
            NLRANDd = diststats(motifsNLRAND)

            motifStats = []
            for pos, key in enumerate(('Entrophy', 'Gini Coeff', 'Fatness')):
                c1 = permttest(NLd[pos], MCId[pos])
                c2 = permttest(NLd[pos], ADd[pos])
                c3 = permttest(NLd[pos], CONVERTd[pos])
                c4 = permttest(MCId[pos], ADd[pos])
                c5 = permttest(MCId[pos], CONVERTd[pos])
                c6 = permttest(ADd[pos], CONVERTd[pos])
                c7 = permttest(NLd[pos], NLRANDd[pos])
                c8 = permttest(MCId[pos], MCIRANDd[pos])
                c9 = permttest(ADd[pos], ADRANDd[pos])
                c10 = permttest(CONVERTd[pos], CONVERTRANDd[pos])
                # ,c7,c8,c9,c10))
                motifStats.append((key, c1, c2, c3, c4, c5, c6))

            f.write(
                "\\begin{table}[t]\n"
                "\\begin{adjustwidth}{-2in}{-2in} "
                "\\caption{Motif Distribution T-test results from " +
                corr + " data with using edge swap}\n"
                "\\centering\n"
                # "\\begin{tabular}{|c|c|c|c|c|c|c|c|c|c|c|}\n"
                "\\begin{tabular}{|c|c|c|c|c|c|c|}\n"
                "\\hline\n"
                "\\rowcolor[gray]{0.85}\n"
                # "Measure & NL to MCI & NL to AD & NL to Conv & MCI to AD & MCI to Conv & AD to Conv & NL to Rand & MCI to Rand & AD to Rand & Conv to Rand \\\\ \\hline\n"
                "Measure & NL to MCI & NL to AD & NL to Conv & MCI to AD & MCI to Conv & AD to Conv \\\\ \\hline\n"
            )
            for stat in motifStats:
                f.write(str(stat[0]) + " \\cellcolor[gray]{0.95}")
                for sign, col in stat[1:]:
                    cell = " & {0:.3}".format(col)
                    if sign > 0:
                        cell += '(+)'
                    else:
                        cell += '(-)'

                    if col <= 0.01:
                        cell += " \\cellcolor{red} "
                    elif col <= 0.05:
                        cell += " \\cellcolor{orange}"
                    elif col <= 0.1:
                        cell += " \\cellcolor{yellow}"
                    f.write(cell)
                f.write("\\\\ \\hline\n")

            f.write(
                "\\end{tabular}\n"
                "\\end{adjustwidth}"
                "\\end{table}\n"
            )

        f.write("\\end{document}\n")

    os.system("pdflatex -output-directory result " + filename)
    os.system("rm result/*.log result/*.aux")


"""""""""""""""""HELPER FUNCTIONS"""""""""""""""""""""


def randomize_graph(G, numpasses):
    "Perfoms numpasses edge swaps in place on G"
    for i in xrange(numpasses):
        success = False
        while not success:
            edges = G.edges()
            edgeSet = set(edges)
            edge1 = rd.choice(edges)
            a, b = edge1
            rd.shuffle(edges)
            for edge2 in edges:
                c, d = edge2
                if (a, d) not in edgeSet and (c, b) not in edgeSet:
                    success = True
                    break
        G.add_edge(a, d)
        G.add_edge(c, b)
        G.remove_edge(a, b)
        G.remove_edge(c, d)


def randomize_graph_count(G, numpasses):
    "Performs numpasses edgeswaps and returns diff from original"
    original = nx.to_numpy_matrix(G)
    diff = [0]
    for i in xrange(numpasses):
        success = False
        while not success:
            edges = G.edges()
            edgeSet = set(edges)
            edge1 = rd.choice(edges)
            a, b = edge1
            rd.shuffle(edges)
            for edge2 in edges:
                c, d = edge2
                if (a, d) not in edgeSet and (c, b) not in edgeSet:
                    success = True
                    break
        G.add_edge(a, d)
        G.add_edge(c, b)
        G.remove_edge(a, b)
        G.remove_edge(c, d)
        newGraph = nx.to_numpy_matrix(G)
        diff.append(np.sum(abs(original - newGraph)) / 2)
    return np.array(diff)


def diststats(graphdict):
    """ Helper Function to calculate entrophy, gini coeff, fatness"""
    listofentrophy = []
    listofgini = []
    listoffatness = []
    for graph in graphdict.iterSortedValues():
        listofentrophy.append(findentrophy(graph))
        listofgini.append(findgini(graph))
        listoffatness.append(findfatness(graph))
    listofentrophy = np.array(listofentrophy)
    listofgini = np.array(listofgini)
    listoffatness = np.array(listoffatness)
    return (listofentrophy, listofgini, listoffatness)


def findentrophy(x):
    sum = 0
    for value in x:
        sum += math.log(value) * value
    return -sum


def findgini(x):
    N = len(x)
    B = sum(xi * (N - i) for i, xi in enumerate(x)) / (N * sum(x))
    return 1 + (1. / N) - 2 * B


def findfatness(x):
    x.sort(reverse=True)
    N = min(int(len(x) / 5), 1)
    return sum(x[:N]) / sum(x[N:])


def rawMotifDataCSV(data):
    pats = ['NL', 'MCI', 'AD', 'CONVERT']
    corrs = ['corr', 'lcorr']
    sizes = [3, 4, 5]

    for pat, corr, size in itertools.product(pats, corrs, sizes):
        filename = "{}{}{}.csv".format(pat, corr, size)
        print(filename)
        with open("MotifRawData/" + filename, "wb") as f:
            writer = csv.writer(f)
            writer.writerow(["Motif ID", "Mean", "STD"])
            data = findMotifs(data, (pat, corr), size)
            for key in data.keys:
                writer.writerow([key, data[key].mean(), data[key].std()])


def rawDistDataCSV(data):
    pats = ['NL', 'MCI', 'AD', 'CONVERT']
    corrs = ['corr', 'lcorr']
    sizes = [3, 4, 5]

    for pat, corr, size in itertools.product(pats, corrs, sizes):
        filename = "Dist{}{}{}.csv".format(pat, corr, size)
        print(filename)
        with open("RawDistStats/" + filename, "wb") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Motif ID", "Gini Mean", "Gini STD", "Entropy Mean", "Entropy STD"])
            data = findMotifs(data, (pat, corr), size)
            for key in data.keys:
                writer.writerow([key, data[key].mean(), data[key].std()])


def rawMotifTTestCSV(data):
    corrs = ['corr', 'lcorr']
    sizes = [3, 4, 5]

    for corr, size in itertools.product(corrs, sizes):
        filename = "NonParametricT_test{}{}.csv".format(corr, size)
        print(filename)

        with open("SwapData10" + ".pkl", "rb") as pic:
            randGraphs = pickle.load(pic)

        # randoms
        print("RANDOMS")
        motifsNLER = findMotifs(data, "rand", motifSize=size)
        motifsADER = findMotifs(data, "rand", motifSize=size)
        motifsNLDD = findMotifs(
            data, ('NL', corr), motifSize=size, randGraphs=randGraphs)
        motifsADDD = findMotifs(
            data, ('AD', corr), motifSize=size, randGraphs=randGraphs)

        # normal datas
        print("Normals")
        motifsNL = findMotifs(data, ('NL', corr), motifSize=size)
        motifsMCI = findMotifs(data, ('MCI', corr), motifSize=size)
        motifsAD = findMotifs(data, ('AD', corr), motifSize=size)
        motifsCONVERT = findMotifs(data, ('CONVERT', corr), motifSize=size)

        NLERkeys = set()
        for dic in motifsNLER:
            NLERkeys.update(set(dic.keys()))

        ADERkeys = set()
        for dic in motifsADER:
            ADERkeys.update(set(dic.keys()))

        NLDDkeys = set()
        for dic in motifsNLDD:
            NLDDkeys.update(set(dic.keys()))

        ADDDkeys = set()
        for dic in motifsADDD:
            ADDDkeys.update(set(dic.keys()))

        allMotifs = list(motifsNL.keys
                         & motifsAD.keys
                         & motifsMCI.keys
                         & motifsCONVERT.keys
                         & NLERkeys
                         & ADERkeys
                         & NLDDkeys
                         & ADDDkeys)

        with open("Motift_testData/" + filename, "wb") as f:
            writer = csv.writer(f)
            writer.writerow(["Motif", "NL/AD", "NL/MCI", "MCI/CONV", "AD/CONV",
                             "NL/ER(NL)", "NL/DD(NL)", "AD/DD(AD)", "AD/ER(AD)"])
            print("t-test")
            total = len(allMotifs)
            for num, key in enumerate(allMotifs):
                print("Key {} of {}".format(num + 1, total))
                norm = motifsNL[key]
                mci = motifsMCI[key]
                ad = motifsAD[key]
                conv = motifsCONVERT[key]
                sign, c1 = permttest(norm, ad)
                sign, c2 = permttest(norm, mci)
                sign, c3 = permttest(mci, conv)
                sign, c4 = permttest(ad, conv)
                sign, c5 = permttest(norm, motifsNLER[key])
                sign, c6 = permttest(norm, motifsNLDD[key])
                sign, c7 = permttest(ad, motifsADDD[key])
                sign, c8 = permttest(ad, motifsADER[key])
                writer.writerow([key, c1, c2, c3, c4, c5, c6, c7, c8])


def rawDistTTestCSV(data):
    corrs = ['corr', 'lcorr']
    sizes = [3, 4, 5]

    for corr, size in itertools.product(corrs, sizes):
        filename = "NonParametricT_test{}{}.csv".format(corr, size)
        print(filename)

        with open("SwapData10" + ".pkl", "rb") as pic:
            randGraphs = pickle.load(pic)

        motifsNLER = findMotifs(data, "rand", motifSize=size)
        NLERd = diststats(motifsNLER)
        motifsADER = findMotifs(data, "rand", motifSize=size)
        ADERd = diststats(motifsADER)
        motifsNLDD = findMotifs(
            data, ('NL', corr), motifSize=size, randGraphs=randGraphs)
        NLDDd = diststats(motifsNLDD)
        motifsADDD = findMotifs(
            data, ('AD', corr), motifSize=size, randGraphs=randGraphs)
        ADDDd = diststats(motifsADDD)

        motifsNL = findMotifs(data, ('NL', corr), motifSize=size)
        NLd = diststats(motifsNL)
        motifsMCI = findMotifs(data, ('MCI', corr), motifSize=size)
        MCId = diststats(motifsMCI)
        motifsAD = findMotifs(data, ('AD', corr), motifSize=size)
        ADd = diststats(motifsAD)
        motifsCONVERT = findMotifs(data, ('CONVERT', corr), motifSize=size)
        CONVERTd = diststats(motifsCONVERT)

        with open("RawDistT_Test/" + filename, "wb") as f:
            writer = csv.writer(f)
            writer.writerow(["Measure", "NL/AD", "NL/MCI", "MCI/CONV",
                             "AD/CONV", "NL/ER(NL)", "NL/DD(NL)", "AD/ER(AD)", "AD/DD(AD)"])
            print("t-test")
            for pos, key in enumerate(('Entrophy', 'Gini Coeff')):
                sign, c1 = permttest(NLd[pos], ADd[pos])
                sign, c2 = permttest(NLd[pos], MCId[pos])
                sign, c3 = permttest(MCId[pos], CONVERTd[pos])
                sign, c4 = permttest(ADd[pos], CONVERTd[pos])
                sign, c5 = permttest(NLd[pos], NLERd[pos])
                sign, c6 = permttest(NLd[pos], NLDDd[pos])
                sign, c7 = permttest(ADd[pos], ADERd[pos])
                sign, c8 = permttest(ADd[pos], ADDDd[pos])
                writer.writerow([key, c1, c2, c3, c4, c5, c6, c7, c8])


def main():
    with open("aznorbert_corrsd_new.pkl", "rb") as f:
        data = pickle.load(f)

    # with open("SwapData" + str(degree) + ".pkl","rb") as pic:
        # randGraphs = pickle.load(pic)

        motifSize = 5

        for corr in ("corr", "lcorr", "lacorr"):
            for ty in ("AD", "MCI", "NL", "CONVERT"):
                for degree in (8, 12):
                    print("Calculating" + str((corr, ty)))
                    findMotifs(data, (ty, corr), motifSize,
                               degree, printMotifs=True)


if __name__ == '__main__':
    main()
