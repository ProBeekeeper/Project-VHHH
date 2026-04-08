# ==========================================
# Core Data Structure: Disjoint Set Union (DSU)
# ==========================================
class DSU:
    """
    Disjoint Set Union (DSU)
    Used to manage groups of elements, quickly determine if two elements belong to the same group,
    and merge two groups.
    In Kruskal's algorithm and player connections, it's used for cycle detection 
    (i.e., checking if two cities are already connected).
    """
    def __init__(self, n):
        """
        Initialize the DSU.
        :param n: Total number of elements (number of cities)
        """
        # parent array: Records the parent of each node. Initially, each node's parent is itself.
        self.parent = list(range(n))
        # rank array: Records the height (rank) of each tree, used for union by rank optimization.
        self.rank = [0] * n

    def find(self, i):
        """
        Find the root node of the set containing node i, with [Path Compression] optimization.
        Path Compression: During the process of finding the root, attach all nodes along the path
        directly to the root node, significantly reducing the time complexity of future finds.
        """
        if self.parent[i] != i:
            self.parent[i] = self.find(self.parent[i])
        return self.parent[i]

    def union(self, i, j):
        """
        Merge the sets containing node i and node j, with [Union by Rank] optimization.
        Union by Rank: Always attach the shorter tree to the root of the taller tree to prevent
        the tree from degrading into a linked list.
        :return: False if i and j are already in the same set (indicates a cycle, already connected);
                 True if successfully merged two different sets.
        """
        root_i = self.find(i)
        root_j = self.find(j)

        if root_i == root_j:
            return False  # Already connected

        # Union by rank
        if self.rank[root_i] < self.rank[root_j]:
            self.parent[root_i] = root_j
        elif self.rank[root_i] > self.rank[root_j]:
            self.parent[root_j] = root_i
        else:
            self.parent[root_j] = root_i
            self.rank[root_i] += 1

        return True
