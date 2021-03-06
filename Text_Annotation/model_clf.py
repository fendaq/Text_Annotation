import tensorflow as tf


def model_clf(input_data=None,
              output_targets=None,
              num_words=3000,
              num_units=128,
              num_layers=2,
              batchsize=64,
              num_tags=10,
              max_seq_len=40):
    '''

    :param input_data:
    :param output_targets:
    :param num_words:
    :param num_units:
    :param num_layers:
    :param batchsize: 1代表生成，大于1代表训练
    :param num_tags:标签数量
    :param max_seq_len: 句子长度
    :return:
    '''
    tensors = {}

    # 一个batch的句子长度序列
    sequence_lengths_t = tf.constant([max_seq_len] * batchsize)

    with tf.name_scope('embedding'):
        w = tf.Variable(tf.random_uniform([num_words, num_units], -1.0, 1.0), name="W")
        # inputs=[?,?,num_units]
        inputs = tf.nn.embedding_lookup(w, input_data)

    with tf.name_scope('lstm'):
        lstmcell = tf.nn.rnn_cell.BasicLSTMCell
        cell_list_f = [lstmcell(num_units, state_is_tuple=True) for i in range(num_layers)]
        cell_mul_f = tf.nn.rnn_cell.MultiRNNCell(cell_list_f, state_is_tuple=True)
        initial_state_f = cell_mul_f.zero_state(batch_size=batchsize, dtype=tf.float32)

        cell_list_b = [lstmcell(num_units, state_is_tuple=True) for i in range(num_layers)]
        cell_mul_b = tf.nn.rnn_cell.MultiRNNCell(cell_list_b, state_is_tuple=True)
        initial_state_b = cell_mul_b.zero_state(batch_size=batchsize, dtype=tf.float32)

        # outputs=[?,?,num_units]
        outputs, last_state = tf.nn.bidirectional_dynamic_rnn(cell_fw=cell_mul_f,
                                                              cell_bw=cell_mul_b,
                                                              inputs=inputs,
                                                              initial_state_fw=initial_state_f,
                                                              initial_state_bw=initial_state_b)

    with tf.name_scope('softmax'):
        output_fw, output_bw = outputs
        output = tf.concat([output_fw, output_bw], axis=-1)
        # output=[?,num_units * 2]
        output = tf.reshape(output, [-1, num_units * 2])
        weights = tf.get_variable("W", [2 * num_units, num_tags])

        # 文本生成的时候用 x*W+b,不知道这里为什么不需要b?
        # bias = tf.Variable(tf.zeros(shape=[num_words]))
        # logits = tf.nn.bias_add(tf.matmul(output, weights), bias=bias)
        logits = tf.matmul(output, weights)

    with tf.name_scope('clf'):
        # batchsize和max_seq_len中的一个可以用-1替代
        # unary_scores [?, max_seq_len, num_tags]
        unary_scores = tf.reshape(logits, [batchsize, -1, num_tags])
        # log_likelihood极大似然估计,[batchsize];transition_params概率转移矩阵[num_tags,num_tags]
        crf_log_likelihood = tf.contrib.crf.crf_log_likelihood(inputs=unary_scores,
                                                               tag_indices=output_targets,
                                                               sequence_lengths=sequence_lengths_t)
        log_likelihood, transition_params = crf_log_likelihood
        decode_tags, best_score = tf.contrib.crf.crf_decode(potentials=unary_scores,
                                                            transition_params=transition_params,
                                                            sequence_length=sequence_lengths_t)

        loss = tf.reduce_mean(-log_likelihood)

    if batchsize > 1:

        train_op = tf.train.AdamOptimizer(learning_rate=0.01).minimize(loss)
        tensors['train_op'] = train_op
        tensors['transition_params'] = transition_params
        tensors['loss'] = loss
        tensors['prediction'] = decode_tags
    else:
        tensors['transition_params'] = transition_params
        tensors['prediction'] = decode_tags

    return tensors


