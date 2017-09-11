/*
 * Copyright 2017 Juang and Liang.
 * file: octo.cpp
 */

#include <omp.h>
#include <hiredis/hiredis.h>

#include <algorithm>
// #define NDEBUG  // uncomment to disable assert()
#include <cassert>
#include <iostream>
#include <random>
#include <set>
#include <string>
#include <vector>

using std::cerr;
using std::cout;
using std::endl;
using std::set;
using std::stod;
using std::stoi;
using std::string;
using std::swap;
using std::vector;

/* Define util functions */
void
gen_target_key(char* key) {
    static const char ALPHANUM[] =
            "0123456789"
            "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
            "abcdefghijklmnopqrstuvwxyz";
    static const size_t LEN = 4;

    std::random_device rd;
    std::default_random_engine gen = std::default_random_engine(rd());
    std::uniform_int_distribution<int> dist(0, (sizeof(ALPHANUM) - 1));

    char unique_id[LEN+1];
    for (size_t i = 0; i < LEN; ++i) {
        unique_id[i] = ALPHANUM[dist(gen)];
    }
    unique_id[LEN] = 0;

    sprintf(key, "target:%s", unique_id);
}

/* Define redis functions */
bool redisinteger(redisContext* c, const char* cmd, int* integer) {
    redisReply* reply = (redisReply*)redisCommand(c, cmd);
    if (reply->type != REDIS_REPLY_INTEGER) {
        cerr << "Error: reply not integer" << endl;
        return false;
    }
    *integer = reply->integer;
    freeReplyObject(reply);
    return true;
}

bool
exists(redisContext* c, const char* key, bool* is_existed) {
    int size = snprintf(nullptr, 0, "EXISTS %s", key);
    char* cmd = new char[size+1];
    sprintf(cmd, "EXISTS %s", key);

    int ret;
    if (!redisinteger(c, cmd, &ret)) {
        cerr << "Error: exists failed" << endl;
        return false;
    }
    *is_existed = (ret == 1);
    delete [] cmd;
    return true;
}

bool
sismember(redisContext* c, const char* key, int member, bool* is_member) {
    int size = snprintf(nullptr, 0, "SISMEMBER %s %d", key, member);
    char* cmd = new char[size+1];
    sprintf(cmd, "SISMEMBER %s %d", key, member);

    int ret;
    if (!redisinteger(c, cmd, &ret)) {
        cerr << "Error: sismember failed" << endl;
        return false;
    }
    *is_member = (ret == 1);
    delete [] cmd;
    return true;
}

bool
scard(redisContext* c, const char* key, int* number) {
    int size = snprintf(nullptr, 0, "SCARD %s", key);
    char* cmd = new char[size+1];
    sprintf(cmd, "SCARD %s", key);

    if (!redisinteger(c, cmd, number)) {
        cerr << "Error: scard failed" << endl;
        return false;
    }
    delete [] cmd;
    return true;
}

bool
sinterstore(redisContext* c, int id1, int id2, int* number) {
    // Doesn't exactly follow redis function. Adjusted for repo.
    int size = snprintf(nullptr, 0,
            "SINTERSTORE repo-inter:%d-%d repo:%d repo:%d", id1, id2, id1, id2);
    char* cmd = new char[size+1];
    sprintf(cmd, "SINTERSTORE repo-inter:%d-%d repo:%d repo:%d",
            id1, id2, id1, id2);

    if (!redisinteger(c, cmd, number)) {
        cerr << "Error: sinterstore failed" << endl;
        return false;
    }
    delete [] cmd;
    return true;
}

bool
del(redisContext* c, const char* key) {
    int size = snprintf(nullptr, 0, "DEL %s", key);
    char* cmd = new char[size+1];
    sprintf(cmd, "DEL %s", key);

    int ret;
    if (!redisinteger(c, cmd, &ret)) {
        cerr << "Error: del failed" << endl;
        return false;
    }
    delete [] cmd;
    return true;
}

bool
zincrby(redisContext* c, const char* key, double increment, int member) {
    redisReply* reply;
    reply = (redisReply*)redisCommand(c, "ZINCRBY %s %f %d",
            key, increment, member);
    if (reply->type != REDIS_REPLY_STRING) {
        cerr << "Error: zincrby reply not string" << endl;
        return false;
    }
    // reply->str
    freeReplyObject(reply);
    return true;
}

bool redisarray(redisContext* c, const char* cmd, vector<int>* array,
                vector<double>* helper_array = nullptr, bool helper = false) {
    redisReply* reply = (redisReply*)redisCommand(c, cmd);
    if (reply->type != REDIS_REPLY_ARRAY) {
        cerr << "Error: reply not array" << endl;
        return false;
    }

    if (helper) {
        array->reserve(reply->elements/2);
        helper_array->reserve(reply->elements/2);
        for (size_t i = 0; i < reply->elements; i += 2) {
            array->push_back(stoi(reply->element[i]->str));
            helper_array->push_back(stod(reply->element[i+1]->str));
        }
    } else {
        array->reserve(reply->elements);
        for (size_t i = 0; i < reply->elements; ++i) {
            array->push_back(stoi(reply->element[i]->str));
        }
    }
    freeReplyObject(reply);
    return true;
}

bool
smembers(redisContext* c, const char* type, int id, vector<int>* members) {
    int size = snprintf(nullptr, 0, "SMEMBERS %s:%d", type, id);
    char* cmd = new char[size+1];
    sprintf(cmd, "SMEMBERS %s:%d", type, id);

    if (!redisarray(c, cmd, members)) {
        cerr << "Error: smembers failed" << endl;
        return false;
    }
    delete [] cmd;
    return true;
}

bool
zrange(redisContext* c, const char* key, int start, int stop,
       vector<int>* elements, vector<double>* score, bool rev) {
    string magic = rev ? "ZREVRANGE" : "ZRANGE";
    int size = snprintf(nullptr, 0, "%s %s %d %d WITHSCORES",
                        magic.c_str(), key, start, stop);
    char* cmd = new char[size+1];
    sprintf(cmd, "%s %s %d %d WITHSCORES", magic.c_str(), key, start, stop);

    if (!redisarray(c, cmd, elements, score, true)) {
        cerr << "Error: z(rev)range failed" << endl;
        return false;
    }
    delete [] cmd;
    return true;
}

/* Main function */
void
octomend_cpp(int redis_port, int target_user, const int* all_repos_array_ptr,
             size_t n_all_repos, const int* orig_repos_array_ptr,
             size_t n_orig_repos, int* top_repos_array_ptr, size_t n_top_repos) {
    redisContext* cxt = redisConnect("localhost", redis_port);
    if (cxt == nullptr || cxt->err) {
        cerr << "Error: connecting redis " << cxt->errstr << endl;
        return;
    }

    const set<int> all_repos_set(all_repos_array_ptr,
                                 all_repos_array_ptr+n_all_repos);
    char target_key[16];
    gen_target_key(target_key);
    bool is_existed;
    if (!exists(cxt, target_key, &is_existed)) return;
    while (is_existed) {
        gen_target_key(target_key);
        if (!exists(cxt, target_key, &is_existed)) return;
    }

    #pragma omp parallel for default(none) num_threads(16) schedule(dynamic) \
            shared(cout, cerr, orig_repos_array_ptr, n_orig_repos, redis_port, \
                   target_user, target_key)
    for (size_t i = 0; i < n_orig_repos; ++i) {
        // cerr << "Now: " << orig_repos_array_ptr[i] << endl;
        redisContext* c = redisConnect("localhost", redis_port);
        if (c == nullptr || c->err) {
            cerr << "Error: connecting redis " << c->errstr << endl;
            continue;
        }
        char key[128];  // Be cautious of buffer overflow regarding sprintf.

        // Get degree of original repo.
        int or_degree;
        sprintf(key, "repo:%d", orig_repos_array_ptr[i]);
        if (!scard(c, key, &or_degree)) continue;

        vector<int> related_users;
        if (!smembers(c, "repo", orig_repos_array_ptr[i], &related_users)) {
            continue;
        }
        for (int ru : related_users) {
            if (ru == target_user) {
                // cerr << "Debug: user back" << endl;
                continue;
            }

            // Get degree of related user.
            int ru_degree;
            sprintf(key, "user:%d", ru);
            if (!scard(c, key, &ru_degree)) continue;
            if (ru_degree > 100) {
                // cerr << "Debug: popular user " << ru << endl;
                continue;
            }

            vector<int> related_repos;
            if (!smembers(c, "user", ru, &related_repos)) continue;
            for (int rr : related_repos) {
                if (all_repos_set.find(rr) != all_repos_set.end()) {
                    // cerr << "Debug: starred repo" << endl;
                    continue;
                }

                // Get degree of related repo.
                int rr_degree;
                sprintf(key, "repo:%d", rr);
                if (!scard(c, key, &rr_degree)) continue;

                // Check if intersection is already calculated.
                int n1 = orig_repos_array_ptr[i];
                int n2 = rr;
                if (n1 > n2) swap(n1, n2);  // Make sure n1 < n2.
                sprintf(key, "repo-inter:%d-%d", n1, n2);
                bool is_existed;
                if (!exists(c, key, &is_existed)) continue;

                // Get degree of intersection between original and related repo.
                int inter_degree;
                if (is_existed) {
                    if (!scard(c, key, &inter_degree)) continue;
                } else {
                    if (!sinterstore(c, n1, n2, &inter_degree)) continue;
                }

                // Calculate score.
                double score = 1.0 * inter_degree /
                    (or_degree + rr_degree - inter_degree);
                if (score != 0) {
                    if (!zincrby(c, target_key, score, rr)) continue;
                }
            }
        }
        redisFree(c);
        cout << ".\n" << std::flush;
    }

    vector<int> top_repos;
    vector<double> top_scores;
    if (!zrange(cxt, target_key, 0, n_top_repos-1, &top_repos, &top_scores,
                true)) {
        return;
    }
    vector<int> last_repos;
    vector<double> last_scores;
    if (!zrange(cxt, target_key, 0, n_top_repos-1, &last_repos, &last_scores,
                false)) {
        return;
    }
    for (size_t i = 0; i < n_top_repos; ++i) {
        cerr << "Info: top repo " << top_repos[i] << ", score " << top_scores[i]
             << ", last repo " << last_repos[i] << ", score " << last_scores[i]
             << endl;
        top_repos_array_ptr[i] = top_repos[i];
        top_repos_array_ptr[n_top_repos+i] = last_repos[i];
    }
    if (!del(cxt, target_key)) return;
    redisFree(cxt);
}

extern "C" {
    void octomend(int redis_port, int target_user,
                  const int* all_repos_array_ptr, size_t n_all_repos,
                  const int* orig_repos_array_ptr, size_t n_orig_repos,
                  int* top_repos_array_ptr, size_t n_top_repos) {
        octomend_cpp(redis_port, target_user,
                     all_repos_array_ptr, n_all_repos,
                     orig_repos_array_ptr, n_orig_repos,
                     top_repos_array_ptr, n_top_repos);
    }
}
