# -*- coding: utf-8 -*-
from builtins import zip
from builtins import range
from ..problem_transform.br import BinaryRelevance

from scipy import sparse


class LabelSpacePartitioningClassifier(BinaryRelevance):
    """Partition label space and classify each subspace separately


    This classifier performs classification by:

    1. partitioning the label space into separate, smaller multi-label sub problems, using the supplied label
    space clusterer

    2. training an instance of the supplied base mult-label classifier for each label space subset in the partition_

    3. predicting the result with each of subclassifiers and returning the sum of their results

    Parameters
    ----------
    classifier : :class:`~sklearn.base.BaseEstimator`
        the base classifier that will be used in a class, will be
        automatically put under :code:`self.classifier`.
    clusterer : :class:`~skmultilearn.cluster.LabelSpaceClustererBase`
        object that partitions the output space, will be
        automatically put under :code:`self.clusterer`.
    require_dense : [bool, bool]
        whether the base classifier requires [input, output] matrices
        in dense representation, will be automatically
        put under :code:`self.require_dense`.

    Attributes
    ----------
    model_count_ : int
        number of trained models, in this classifier equal to the number of partitions
    partition_ : List[List[int]], shape=(`model_count_`,)
        list of lists of label indexes, used to index the output space matrix, set in :meth:`_generate_partition`
        via :meth:`fit`
    classifiers : List[:class:`~sklearn.base.BaseEstimator`], shape=(`model_count_`,)
        list of classifiers trained per partition, set in :meth:`fit`


    References
    ----------

    If you use this clusterer please cite the clustering paper:

    .. code:: latex

        @Article{datadriven,
            author = {Szymański, Piotr and Kajdanowicz, Tomasz and Kersting, Kristian},
            title = {How Is a Data-Driven Approach Better than Random Choice in
            Label Space Division for Multi-Label Classification?},
            journal = {Entropy},
            volume = {18},
            year = {2016},
            number = {8},
            article_number = {282},
            url = {http://www.mdpi.com/1099-4300/18/8/282},
            issn = {1099-4300},
            doi = {10.3390/e18080282}
        }

    Examples
    --------
    Here's an example of building a partitioned ensemble of Classifier Chains

    .. code :: python

        from skmultilearn.ensemble import MajorityVotingClassifier
        from skmultilearn.cluster import FixedLabelSpaceClusterer
        from skmultilearn.problem_transform import ClassifierChain
        from sklearn.naive_bayes import GaussianNB


        classifier = MajorityVotingClassifier(
            clusterer = FixedLabelSpaceClusterer(clusters = [[1,3,4], [0, 2, 5]]),
            classifier = ClassifierChain(classifier=GaussianNB())
        )
        classifier.fit(X_train,y_train)
        predictions = classifier.predict(X_test)

    More advanced examples can be found in :doc:`../labelrelations.ipynb`.

    """

    def __init__(self, classifier=None, clusterer=None, require_dense=None):
        super(LabelSpacePartitioningClassifier, self).__init__(classifier, require_dense)
        self.clusterer = clusterer
        self.copyable_attrs = ['clusterer', 'classifier', 'require_dense']

    def predict(self, X):
        """Predict labels for X

        Parameters
        ----------
        X : numpy.ndarray or scipy.sparse.csc_matrix
            input features of shape :code:`(n_samples, n_features)`

        Returns
        -------
        scipy.sparse of int
            binary indicator matrix with label assignments with shape
            :code:`(n_samples, n_labels)`
        """
        X = self._ensure_input_format(
            X, sparse_format='csr', enforce_sparse=True)
        result = sparse.lil_matrix((X.shape[0], self.label_count), dtype=int)

        for model in range(self.model_count):
            predictions = self._ensure_output_format(self.classifiers_[model].predict(
                X), sparse_format=None, enforce_sparse=True).nonzero()
            for row, column in zip(predictions[0], predictions[1]):
                result[row, self.partition_[model][column]] = 1

        return result

    def _generate_partition(self, X, y):
        """Cluster the label space

        Saves the partiton generated by the clusterer to :code:`self.partition_` and
        sets :code:`self.model_count_` to number of clusers and :code:`self._label_count`
        to number of labels.

        Parameters
        -----------
        X : numpy.ndarray or scipy.sparse
            input features of shape :code:`(n_samples, n_features)`, passed to clusterer
        y : numpy.ndarray or scipy.sparse
            binary indicator matrix with label assigments of shape
            :code:`(n_samples, n_labels)`

        Returns
        -------
        LabelSpacePartitioningClassifier
            returns an instance of itself
        """

        self.partition_ = self.clusterer.fit_predict(X, y)
        self.model_count_ = len(self.partition_)
        self._label_count = y.shape[1]

        return self
