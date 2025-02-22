
from random import choice,randint,random,sample,choices
from scipy.special import gamma as GAMMA
from scipy.stats import nbinom, gamma, binom, expon, poisson
from transmission_models.priors.partial_sampled_utils import *
import numpy as np
import transmission_models.utils as utils
from itertools import combinations
import networkx as nx

class genetic_prior_tree():
    def __init__(self, model, mu, distance_matrix):
        self.mu = mu
        self.distance_matrix = distance_matrix

        self.prior_dist = poisson(mu)

        self.model = model

        self.correction_LL = 0
        self.log_prior = 0

    @staticmethod
    def search_firsts_sampled_siblings(host, T, distance_matrix):

        sampled_hosts = []
        for h in T.successors(host):
            if not np.isnan(distance_matrix[int(h),int(h)]) and h.sampled:#If sampled
                sampled_hosts.append(h)
            else:
                sampled_hosts += genetic_prior_tree.search_firsts_sampled_siblings(h, T, distance_matrix)

        return sampled_hosts

    @staticmethod
    def search_first_sampled_parent(host, T, root):

        if host == root:
            return None

        parent = next(T.predecessors(host))

        if not parent.sampled:
            return genetic_prior_tree.search_first_sampled_parent(parent, T, root)
        else:
            return parent
    @staticmethod
    def get_mut_time_dist(hp, hs):
        return (hs.t_sample + hp.t_sample - 2 * hp.t_inf)

    def get_closest_sampling_siblings(self,T=None,verbose=False):
        if T is None:
            T = self.model.T
            # self.model.get_root_subtrees()

        roots_subtrees = get_roots_data_subtrees(self.model.root_host, T, self.distance_matrix)
        non_observed = list(roots_subtrees)
        LL_correction = 0
        # print(roots_subtrees[::-1],shuffle(roots_subtrees[::-1]))
        if verbose:
            print("Top correction\n","_"*20)
        for h in roots_subtrees:
            if h not in non_observed: continue
            N_samp = 0
            parent = h
            relatives = []
            jumped = False
            closest = None
            while N_samp == 0:
                parent = list(T.predecessors(parent))[0]
                closest = None
                # print(h,parent)
                if parent != self.model.root_host:
                    if T.out_degree(parent) == 1:
                        # parent = model.parent(parent)
                        # print(h,parent)
                        jumped = True
                        continue
                    # elif model.out_degree(parent)==2 and not jumped:
                    #     parent = model.parent(parent)
                    #     jumped = True
                    #     continue

                for h2 in T.successors(parent):
                    # print("-"*6,h,parent,h2)
                    if h2.sampled:
                        if h2 == h or np.isnan(self.distance_matrix[int(h2),int(h2)]):
                            continue
                        else:
                            # if h2 not in non_observed: continue
                            # print("KAKA2",h2,parent)
                            N_samp += 1
                            relatives.append(h2)
                            # non_observed.remove(h2)
                    # else:
                    # print("KAKA",h2,parent)
                if parent == self.model.root_host: break
            # non_observed.remove(h)
            if not relatives: continue
            closest = min(relatives, key=lambda h2: h2.t_sample)
            Dt = (closest.t_sample + h.t_sample - 2 * parent.t_inf)
            LL_correction += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(closest)]))
            if verbose:
                print(f"\t\t{int(h),int(closest)},{Dt=} {self.distance_matrix[int(h), int(closest)]=} {np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(closest)]))}")

            # print("----->",h,closest,parent)
        return LL_correction

    # def get_closest_sampling_siblings(self):
    #     non_observed = list(self.model.roots_subtrees)
    #     LL_correction = 0
    #
    #     for h in self.model.roots_subtrees:
    #         if h not in non_observed: continue
    #         N_samp = 0
    #         parent = h
    #         relatives = []
    #         jumped = False
    #         closest = None
    #         while N_samp == 0:
    #             parent = self.model.parent(parent)
    #             closest = None
    #             # print(h,parent)
    #             if parent != self.model.root_host:
    #                 if self.model.out_degree(parent) == 1:
    #                     # parent = model.parent(parent)
    #                     # print(h,parent)
    #                     jumped = True
    #                     continue
    #                 # elif model.out_degree(parent)==2 and not jumped:
    #                 #     parent = model.parent(parent)
    #                 #     jumped = True
    #                 #     continue
    #
    #             for h2 in self.model.successors(parent):
    #                 # print("-"*6,h,parent,h2)
    #                 if h2.sampled:
    #                     if h2 == h:
    #                         continue
    #                     elif not h2.sampled:
    #                         continue
    #                     else:
    #                         # if h2 not in non_observed: continue
    #                         # print("KAKA2",h2,parent)
    #                         N_samp += 1
    #                         relatives.append(h2)
    #                         # non_observed.remove(h2)
    #                 # else:
    #                 # print("KAKA",h2,parent)
    #             if parent == self.model.root_host: break
    #         # non_observed.remove(h)
    #         if relatives == []: continue
    #         closest = min(relatives, key=lambda h2: h2.t_sample)
    #         Dt = (closest.t_sample + h.t_sample - 2 * parent.t_inf)
    #         # print(f"\t\t{int(pair[0]),int(pair[1])},{Dt`=}")
    #         LL_correction += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(closest)]))
    #
    #         # print("----->",h,closest,parent)
    #     return LL_correction

    def prior_host(self, host, T, parent_dist=False):
        log_prior = 0
        for h2 in T[host]:
            if h2.sampled:
                # print(f"{host}-->{h2}")
                Dt = h2.t_sample - host.t_sample
                log_prior += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(h2)]))
                p = poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(h2)])
                # print(int(h),int(h2),Dt,p,np.log(p))
            else:
                siblings = genetic_prior_tree.search_firsts_sampled_siblings(h2, T, self.distance_matrix)
                for hs in siblings:
                    # print(f"{host}-->{hs}")
                    Dt = hs.t_sample - host.t_sample
                    log_prior += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(hs)]))
        if parent_dist and host != self.model.root_host:
            parent = self.model.parent(host)
            if parent.sampled:
                Dt = host.t_sample - parent.t_sample
                log_prior += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(parent)]))
            else:
                parent = genetic_prior_tree.search_first_sampled_parent(host, T, self.model.root_host)
                if parent is not None:
                    # print(f"{parent}-->{host}")
                    Dt = host.t_sample - parent.t_sample
                    log_prior += np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(parent)]))

        return log_prior

    def prior_pair(self, h1, h2):
        log_prior = 0
        if not h1.sampled or not h2.sampled:
            return 0
        Dt = h2.t_sample - h1.t_sample
        return np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h1), int(h2)]))

    def log_prior_host_list(self,host_list,T=None):
        log_prior = 0
        for host in host_list:
            log_prior += self.log_prior_host(host,T)
        return log_prior

    def log_prior_host(self,host,T=None):
        """
        Calculate the prior of a host
        Args:
            host:

        Returns:

        """
        if T is None:
            T = self.model.T
        sampled_siblings = genetic_prior_tree.search_firsts_sampled_siblings(host, T, self.distance_matrix)
        log_prior = 0
        for h2 in sampled_siblings:

            Dt = self.get_mut_time_dist(host, h2)
            lp = np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(host), int(h2)]))
            # print(host,h2,lp)
            log_prior += lp
        return log_prior

    def log_prior_T(self, T, update_up=True,verbose=False):
        self.log_prior = 0
        suma = 0
        for h in T:
            if np.isnan(self.distance_matrix[int(h),int(h)]) or not h.sampled:continue#Check if we have info of h
            for h2 in T[h]:
                if not np.isnan(self.distance_matrix[int(h2), int(h2)]) and h2.sampled:  # Check if we have info of h2
                    # print(f"{h}-->{h2}  {self.distance_matrix[int(h2), int(h2)]}")
                    Dt = h2.t_sample - h2.t_inf + np.abs(h.t_sample - h2.t_inf)

                    log_L = np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(h2)]))
                    if verbose: print(f"{h}-->{h2} {Dt=} {log_L=}")
                    suma += log_L
                    self.log_prior += log_L
                    # p = poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(h2)])
                    # print(int(h),int(h2),Dt,p,np.log(p))
                else:
                    siblings = genetic_prior_tree.search_firsts_sampled_siblings(h2, T, self.distance_matrix)
                    for hs in siblings:
                        if np.isnan(self.distance_matrix[int(hs),int(hs)]) or not hs.sampled:continue
                        # print(f"{h}-->{hs} (jumped) {self.distance_matrix[int(h),int(hs)]}, {hs.sampled}")
                        Dt =  hs.t_sample - h2.t_inf + np.abs(h.t_sample - h2.t_inf)
                        log_L = np.log(poisson(self.mu * Dt).pmf(self.distance_matrix[int(h), int(hs)]))
                        if verbose: print(f"{h}-->{hs} (jumped) {Dt=} {log_L=}")
                        suma += log_L
                        self.log_prior += log_L
        if verbose: print(f"{suma=}")

        if update_up:
            # self.model.get_root_subtrees()
            LL_correction = self.get_closest_sampling_siblings(T)

            self.correction_LL = LL_correction
            self.log_prior += LL_correction
        else:
            self.correction_LL = 0
        # print(f"{self.correction_LL-self.log_prior=},{self.correction_LL=}")
        return self.log_prior

    def Delta_log_prior(self, host, T_end, T_ini):

        Delta = 0
        if not host.sampled:
            return 0

        if T_ini is None:
            T_ini = self.model.T

        # Parent
        if host != self.model.root_host:
            # Ini
            parent = genetic_prior_tree.search_first_sampled_parent(host, T_ini, model.root_host)
            if parent is None:
                D_time_ini = 0
                D_gen_ini = 0
                LL_ini = 0
            else:
                D_time_ini = host.t_sample - parent.t_sample
                D_gen_ini = self.distance_matrix[host.index, parent.index]
                LL_ini = np.log(p.prior_dist.pmf(D_time_ini * D_gen_ini))
            # print("parent ini",D_time_ini,D_gen_ini,LL_ini)

            # End
            parent = genetic_prior_tree.search_first_sampled_parent(host, T_end, model.root_host)
            if parent is None:
                D_time_end = 0
                D_gen_end = 0
                LL_end = 0
            else:
                D_time_end = host.t_sample - parent.t_sample
                D_gen_end = self.distance_matrix[host.index, parent.index]
                LL_end = np.log(p.prior_dist.pmf(D_time_end * D_gen_end))

            # print("parent end",D_time_end,D_gen_end,LL_end)
            Delta += LL_end - LL_ini

        # Sons
        siblings = genetic_prior_tree.search_firsts_sampled_siblings(host, T_ini, self.distance_matrix)
        LL = 0
        for h in siblings:
            D_time = h.t_sample - host.t_sample
            D_gen = self.distance_matrix[host.index, h.index]
            LL -= np.log(p.prior_dist.pmf(D_time * D_gen))
            # print("sibling ini",D_time,D_gen,LL,p.prior_dist.pmf(D_time*D_gen))

        siblings = genetic_prior_tree.search_firsts_sampled_siblings(host, T_end, self.distance_matrix)
        for h in siblings:
            D_time = h.t_sample - host.t_sample
            D_gen = self.distance_matrix[host.index, h.index]
            LL += np.log(p.prior_dist.pmf(D_time * D_gen))

        Delta += LL

        return Delta



def get_roots_data_subtrees(host, T, dist_matrix):
    sampled_hosts = []
    for h in T.successors(host):
        if not np.isnan(dist_matrix[int(h), int(h)]) and h.sampled:
            sampled_hosts.append(h)
        else:
            sampled_hosts += get_roots_data_subtrees(h, T, dist_matrix)

    return sampled_hosts
