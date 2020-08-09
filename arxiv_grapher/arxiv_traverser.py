import arxiv
import pandas as pd
import queue
from collections import defaultdict
import networkx as nx
import logging
import ast

logger = logging.getLogger()

# TODO : test discovery BFS Traversal
# TODO : traverse people, but then in the final plot, only show people maximally X distance away


def discovery_BFS_traversal(root, max_depth, next_traversal_f):
    """
    Traverse from a root BFS, 
    apply next_traversal_f to get the next set of vertices
    :param root: 
    :param max_depth: [int] - max depth to traverse graph using BFS
    :param next_traversal_f: function(obj) - returns a list of objects to add to the queue 
    """
    Q = queue.Queue()
    discovered = set()

    discovered.add(root)
    Q.put(root)
    depth = 0
    timeToDepthIncrease = 1

    while not Q.empty() and depth <= max_depth:
        v = Q.get()
        timeToDepthIncrease -= 1
        adjacent_vs = next_traversal_f(v)
        for w in adjacent_vs:
            if w not in discovered:
                Q.put(w)
                discovered.add(w)

        if timeToDepthIncrease == 0:
            depth += 1
            logger.debug(f"increase depth to {depth}")
            timeToDepthIncrease = Q.qsize()


def search(search_query, max_search_results=10000):
    logging.debug(f"searching : {search_query}")
    df = pd.DataFrame(arxiv.query(search_query,
                                  max_results=max_search_results))
    return df


def BFS_author_query(original_author, max_search_results=10, max_depth=5):
    """ Traverse the papers by coauthors and return a list of all the articles """
    original_author = original_author.lower()
    def next_traversal_vertices(author, all_articles):
        """ 
        return list of things to bump onto the queue, to traversal 1 deeper level
        also also update all_articles while on the way 
        HACK - all_articles is a list around a dataframe, to be able to pass by reference
            all_articles = [df.DataFrame], this allows one to update it
        """
        # get arxiv articles for a specific search
        arxiv_articles = search(author, max_search_results=max_search_results)
        # return True if author is a coauthor of article
        is_coauthor = lambda row: any([author.lower() == article_author.lower() for article_author in row.authors])
        # get df of coauthored articles
        coauthored_articles = arxiv_articles[arxiv_articles.apply(is_coauthor,
                                                                  axis=1)]

        # update the master list of articles
        all_articles[0] = all_articles[0].append(coauthored_articles,
                                                 ignore_index=True)

        # get a list of all the coauthors
        unique_coauthors = set()
        for author_list in coauthored_articles.authors:
            for author in author_list:
                unique_coauthors.add(author.lower())

        return unique_coauthors

    # partially apply next_traversal_verticies to only take author as an arg, but to update the all_articles
    all_articles = [pd.DataFrame()]
    next_traversal_vertices_partially_applied = lambda author: next_traversal_vertices(
        author, all_articles)

    discovery_BFS_traversal(
        original_author,
        max_depth=max_depth,
        next_traversal_f=next_traversal_vertices_partially_applied)
    return all_articles[0]


def get_authors_to_articles(all_articles):
    """ 
    helper function # TODO - currently this function isn't used
    input : dataframe of all articles
    returns : dict of author_name to article ids
    """
    author_to_articles = defaultdict(lambda: list)
    for _, row in all_articles.iterrows():
        for author in row.authors:
            author_to_articles[author].append(row.article)
    return author_to_articles


def _create_edge(author1, author2, G):
    if G.has_edge(author1, author2):
        G[author1][author2]['weight'] += 1
    else:
        G.add_edge(author1, author2, weight=1)


def generate_author_graph(all_articles):
    """ return networkx graph of all the authors, with weights between them based on their shared papers"""
    G = nx.Graph()
    for authors in all_articles.authors:
        # Lists are sometimes read into a string, convert it back to a list
        if isinstance(authors,str):
            authors = ast.literal_eval(authors)
        
        for i in range(len(authors)):
            for j in range(i + 1, len(authors)):
                _create_edge(authors[i], authors[j], G)
    return G
