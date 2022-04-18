Feature: Shamir Protocol

    Scenario Outline: Startup Reliability
        Given <players> players
        Then it should be possible to setup a shamir protocol object <count> times

        Examples:
        | players | count   |
        | 3       | 100     |
        | 4       | 100     |
        | 10      | 100     |


    Scenario: Inter-session Repetition
        Given 3 players
        When shamir secret sharing the same value for 10 sessions
	    Then the shares should never be repeated


    Scenario: Intra-session Repetition
        Given 3 players
        When shamir secret sharing the same value 10 times in one session
        Then the shares should never be repeated

    Scenario Outline: Random Round Trip Shamir Sharing
        Given <players> players 
        When player <player> shamir shares and reveals random secrets, the revealed secrets should match the originals

        Examples:
        | players | player |
        | 3       | 0      |
        | 4       | 0      |
        | 5       | 0      |

    Scenario Outline: Local Shamir Addition
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place addition on the shamir shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                 |
        | 3       | 5       | 1.1         | 1      | [6.1] * 3                              |
        | 4       | 5       | 1.5         | 2      | [6.5] * 4                              |

        | 3       | [5, 3]  | [1.1, 2.2]  | 1      | [[6.1, 5.2]] * 3                       |


    Scenario Outline: Local Shamir Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place subtraction on the shamir shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |


    Scenario Outline: Shamir Addition
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation               | a  | b    | count | result              |
        | 3       | public-private addition | -2 | -3.5 | 10    | [[-5.5] * 3] * 10   |
        | 3       | public-private addition | -20 | -30 | 10    | [[-50] * 3] * 10   |
        | 3       | public-private addition | -200 | -300 | 10    | [[-500] * 3] * 10   |
        | 3       | public-private addition | -2000 | -3000 | 10    | [[-5000] * 3] * 10   |
        | 3       | public-private addition | -20000 | -30000 | 10    | [[-50000] * 3] * 10   |
        | 3       | public-private addition | -200000 | -300000 | 10    | [[-500000] * 3] * 10   |
        | 3       | public-private addition | -2000000 | -3000000 | 10    | [[-5000000] * 3] * 10   |
        | 3       | public-private addition | -20000000 | -30000000 | 10    | [[-50000000] * 3] * 10   |
        | 3       | public-private addition | -200000000 | -300000000 | 10    | [[-500000000] * 3] * 10   |
        | 3       | public-private addition | -21 | -35 | 10    | [[-56] * 3] * 10   |
        | 3       | public-private addition | -212 | -351 | 10    | [[-563] * 3] * 10   |
        | 3       | public-private addition | -2123 | -3512 | 10    | [[-5635] * 3] * 10   |
        | 3       | public-private addition | -21234 | -35123 | 10    | [[-56357] * 3] * 10   |
        | 3       | public-private addition | -212345 | -351234 | 10    | [[-563579] * 3] * 10   |
        | 3       | public-private addition | -2123456 | -3512345 | 10    | [[-5635801] * 3] * 10   |
        | 3       | public-private addition | -21234567 | -35123458 | 10    | [[-56358025] * 3] * 10   |
        | 3       | public-private addition | -212345678 | -351234589 | 10    | [[-563580267] * 3] * 10   |

        | 3       | private-private addition | -2 | -3.5 | 10    | [[-5.5] * 3] * 10   |
        | 3       | private-private addition | -20 | -30 | 10    | [[-50] * 3] * 10   |
        | 3       | private-private addition | -200 | -300 | 10    | [[-500] * 3] * 10   |
        | 3       | private-private addition | -2000 | -3000 | 10    | [[-5000] * 3] * 10   |
        | 3       | private-private addition | -20000 | -30000 | 10    | [[-50000] * 3] * 10   |
        | 3       | private-private addition | -200000 | -300000 | 10    | [[-500000] * 3] * 10   |
        | 3       | private-private addition | -2000000 | -3000000 | 10    | [[-5000000] * 3] * 10   |
        | 3       | private-private addition | -20000000 | -30000000 | 10    | [[-50000000] * 3] * 10   |
        | 3       | private-private addition | -200000000 | -300000000 | 10    | [[-500000000] * 3] * 10   |
        | 3       | private-private addition | -21 | -35 | 10    | [[-56] * 3] * 10   |
        | 3       | private-private addition | -212 | -351 | 10    | [[-563] * 3] * 10   |
        | 3       | private-private addition | -2123 | -3512 | 10    | [[-5635] * 3] * 10   |
        | 3       | private-private addition | -21234 | -35123 | 10    | [[-56357] * 3] * 10   |
        | 3       | private-private addition | -212345 | -351234 | 10    | [[-563579] * 3] * 10   |
        | 3       | private-private addition | -2123456 | -3512345 | 10    | [[-5635801] * 3] * 10   |
        | 3       | private-private addition | -21234567 | -35123458 | 10    | [[-56358025] * 3] * 10   |
        | 3       | private-private addition | -212345678 | -351234589 | 10    | [[-563580267] * 3] * 10   |

    Scenario Outline: Untruncated Shamir Multiplication
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                                  | a   | b    | count | result                |
        | 3       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 3] * 10       |
        | 3       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 3] * 10     |
        | 3       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 3] * 10    |
        | 3       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 3] * 10     |
        | 3       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 3] * 10       |
        | 4       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 4] * 10       |
        | 4       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 4] * 10     |
        | 4       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 4] * 10    |
        | 4       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 4] * 10     |
        | 4       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 4] * 10       |
        | 5       | private-private untruncated multiplication | 5   | 2    | 10    | [[655360] * 5] * 10       |
        | 5       | private-private untruncated multiplication | 5   | 2.5  | 10    | [[819200] * 5] * 10     |
        | 5       | private-private untruncated multiplication | 5   | -2.5 | 10    | [[-819200] * 5] * 10    |
        | 5       | private-private untruncated multiplication | -5  | -2.5 | 10    | [[819200] * 5] * 10     |
        | 5       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 10    | [[[655360, 917504]] * 5] * 10       |


    Scenario Outline: Shamir Logical Exclusive Or
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation           | a      | b      | count | result             |
        | 5       | private-private xor | 0      | 0      | 10    | [[0] * 5] * 10     |
        | 5       | private-private xor | 0      | 1      | 10    | [[1] * 5] * 10     |
        | 5       | private-private xor | 1      | 0      | 10    | [[1] * 5] * 10     |
        | 5       | private-private xor | 1      | 1      | 10    | [[0] * 5] * 10     |


    Scenario Outline: Shamir Logical Or
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a      | b      | count | result             |
        | 5       | private-private or | 0      | 0      | 10    | [[0] * 5] * 10     |
        | 5       | private-private or | 0      | 1      | 10    | [[1] * 5] * 10     |
        | 5       | private-private or | 1      | 0      | 10    | [[1] * 5] * 10     |
        | 5       | private-private or | 1      | 1      | 10    | [[1] * 5] * 10     |


    Scenario Outline: Shamir Max
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a              | b                  | count | result                         |
        | 3       | max                | 2              | 3.5                | 10    | [[3.5] * 3] * 10               |
        | 3       | max                | 3.5            | 2                  | 10    | [[3.5] * 3] * 10               |
        | 3       | max                | -3             | 2                  | 10    | [[2] * 3] * 10                 |
        | 3       | max                | 2              | -3                 | 10    | [[2] * 3] * 10                 |
        | 3       | max                | -4             | -3                 | 10    | [[-3] * 3] * 10                |
        | 3       | max                | [2, 3, -2, -1] | [3.5, 1, 1, -4]    | 10    | [[[3.5, 3, 1, -1]] * 3] * 10   |


    Scenario Outline: Shamir Min
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a              | b                  | count | result                         |
        | 3       | min                | 2              | 3.5                | 10    | [[2] * 3] * 10                 |
        | 3       | min                | 3.5            | 2                  | 10    | [[2] * 3] * 10                 |
        | 3       | min                | -3             | 2                  | 10    | [[-3] * 3] * 10                |
        | 3       | min                | 2              | -3                 | 10    | [[-3] * 3] * 10                |
        | 3       | min                | -4             | -3                 | 10    | [[-4] * 3] * 10                |
        | 3       | min                | [2, 3, -2, -1] | [3.5, 1, -2, -4]   | 10    | [[[2, 1, -2, -4]] * 3] * 10    |


    Scenario Outline: Shamir Random Bitwise Secret
        Given <players> players
        Then generating <bits> shamir random bits with all players produces a valid result

        Examples:
        | players | bits  |
        | 4       | 1     |
        | 4       | 2     | 
        | 4       | 4     |  
        | 4       | 8     |
        | 3       | 8     |
        | 3       | 8     |


    Scenario Outline: Shamir Multiplication
        Given <players> players
        And binary operation shamir <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                      | a   | b    | count | result                |
        | 6       | private-private multiplication | 5   | 2    | 10    | [[10] * 6] * 10       |
        | 6       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 6] * 10     |
        | 6       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 6] * 10    |
        | 6       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 6] * 10     |
        | 6       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 6] * 10       |
        | 3       | private-private multiplication | 5   | 2    | 10    | [[10] * 3] * 10       |
        | 3       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 3] * 10     |
        | 3       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 3] * 10    |
        | 3       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 3] * 10     |
        | 3       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 3] * 10       |
        | 4       | private-private multiplication | 5   | 2    | 10    | [[10] * 4] * 10       |
        | 4       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 4] * 10     |
        | 4       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 4] * 10    |
        | 4       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 4] * 10     |
        | 4       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 4] * 10       |
        | 5       | private-private multiplication | 5   | 2    | 10    | [[10] * 5] * 10       |
        | 5       | private-private multiplication | 5   | 2.5  | 10    | [[12.5] * 5] * 10     |
        | 5       | private-private multiplication | 5   | -2.5 | 10    | [[-12.5] * 5] * 10    |
        | 5       | private-private multiplication | -5  | -2.5 | 10    | [[12.5] * 5] * 10     |
        | 5       | private-private multiplication | [5, 3.5]   | [2, 4]  | 10    | [[[10, 14]] * 5] * 10       |


    Scenario Outline: Shamir Floor
        Given <players> players
        And unary operation shamir <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a             | count | result               |
        | 4       | floor     | 1             | 10    | [[1] * 4] * 10       |
        | 4       | floor     | 1.1           | 10    | [[1] * 4] * 10       |
        | 4       | floor     | -2            | 10    | [[-2] * 4] * 10      |
        | 4       | floor     | -2.1          | 10    | [[-3] * 4] * 10      |
        | 4       | floor     | [1.2, -3.4]   | 10    | [[[1, -4]] * 4] * 10 |
        | 3       | floor     | 1             | 10    | [[1] * 3] * 10       |
        | 3       | floor     | 1.1           | 10    | [[1] * 3] * 10       |
        | 3       | floor     | -2            | 10    | [[-2] * 3] * 10      |
        | 3       | floor     | -2.1          | 10    | [[-3] * 3] * 10      |
        | 3       | floor     | [1.2, -3.4]   | 10    | [[[1, -4]] * 3] * 10 |


    Scenario Outline: Shamir Equality
        Given <players> players
        And binary operation shamir private-private equality
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a                 | b                | count | result                        |
        | 5        | 2                 | 2                | 10    | [[1] * 5] * 10                |
        | 5        | 2                 | 3                | 10    | [[0] * 5] * 10                |
        | 5        | 2                 | 2.1              | 10    | [[0] * 5] * 10                |
        | 5        | 2.1               | 2.1              | 10    | [[1] * 5] * 10                |
        | 5        | -2                | -2               | 10    | [[1] * 5] * 10                |
        | 5        | -2                | -3               | 10    | [[0] * 5] * 10                |
        | 5        | -2                | -2.1             | 10    | [[0] * 5] * 10                |
        | 5        | -2.1              | -2.1             | 10    | [[1] * 5] * 10                |
        | 5        | -2                | 2                | 10    | [[0] * 5] * 10                |
        | 3        | [1, -2, 3, -4.5]  | [1, 2, 3, -4.5]  | 10    | [[[1,0,1,1]] * 3] * 10        |


  @wip
    Scenario Outline: Shamir Modulus
        Given <players> players
        And binary operation shamir private-public modulus
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a                 | b                | count | result                          |
        | 3        | 144409            | 117              | 10    | [[144409 % 117] * 3] * 10       |
        | 3        | 144409            | 118              | 10    | [[144409 % 118] * 3] * 10       |
        | 3        | 144409            | 119              | 10    | [[144409 % 119] * 3] * 10       |
        | 3        | 144409            | 120              | 10    | [[144409 % 120] * 3] * 10       |
        | 3        | 144409            | 121              | 10    | [[144409 % 121] * 3] * 10       |
        | 3        | 144409            | 122              | 10    | [[144409 % 122] * 3] * 10       |
        | 3        | 144409            | 123              | 10    | [[144409 % 123] * 3] * 10       |
        | 3        | 144409            | 124              | 10    | [[144409 % 124] * 3] * 10       |
        | 3        | 144409            | 125              | 10    | [[144409 % 125] * 3] * 10       |
        | 3        | 144409            | 126              | 10    | [[144409 % 126] * 3] * 10       |

    Scenario Outline: Shamir Multiplicative Inverse
        Given <players> players
        And unary operation shamir <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation               | a                                 | count | result                      |
        | 4       | multiplicative_inverse  | 2                                 | 10    | [[1] * 4] * 10              |
        | 4       | multiplicative_inverse  | 100                               | 10    | [[1] * 4] * 10              |
        | 4       | multiplicative_inverse  | -75                               | 10    | [[1] * 4] * 10              |
        | 4       | multiplicative_inverse  | -1000                             | 10    | [[1] * 4] * 10              |
        | 4       | multiplicative_inverse  | [[35.125,65.25],[73.5, -3.0625]]  | 10    | [[[[1,1],[1,1]]] * 4] * 10  |
        | 3       | multiplicative_inverse  | 2                                 | 10    | [[1] * 3] * 10              |
        | 3       | multiplicative_inverse  | 100                               | 10    | [[1] * 3] * 10              |
        | 3       | multiplicative_inverse  | -75                               | 10    | [[1] * 3] * 10              |
        | 3       | multiplicative_inverse  | -1000                             | 10    | [[1] * 3] * 10              |
        | 3       | multiplicative_inverse  | [[35.125,65.25],[73.5, -3.0625]]  | 10    | [[[[1,1],[1,1]]] * 3] * 10  |


    Scenario Outline: Shamir Less
        Given <players> players
        And binary operation shamir less 
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 0              | 10    | [[0] * 3] * 10                  |
        | 3        | 0             | 100            | 10    | [[1] * 3] * 10                  |
        | 3        | 0             | -100           | 10    | [[0] * 3] * 10                  |
        | 3        | 0             | 2**-16         | 10    | [[1] * 3] * 10                  |
        | 3        | 0             | -2**-16        | 10    | [[0] * 3] * 10                  |
        | 3        | -100          | 100            | 10    | [[1] * 3] * 10                  |
        | 3        | 100           | 100            | 10    | [[0] * 3] * 10                  |
        | 3        | -100          | -100           | 10    | [[0] * 3] * 10                  |
        | 3        | 2**16         | 2**16-1        | 10    | [[0] * 3] * 10                  |
        | 3        | 2**16-2       | 2**16-1        | 10    | [[1] * 3] * 10                  |
        | 3        | [[1,2],[3,4]] | [[2,2],[4,4]]  | 10    | [[[[1,0],[1,0]]] * 3] * 10      |


    Scenario Outline: Shamir ReLU 
        Given <players> players
        And unary operation shamir <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a                       | count | result                          |
        | 4       | relu      | 1                       | 10    | [[1] * 4] * 10                  |
        | 4       | relu      | 1.1                     | 10    | [[1.1] * 4] * 10                |
        | 4       | relu      | -2                      | 10    | [[0] * 4] * 10                  |
        | 4       | relu      | -2.1                    | 10    | [[0] * 4] * 10                  |
        | 4       | relu      | [[0, 3.4],[-1234,1234]] | 10    | [[[[0,3.4],[0,1234]]] * 4] * 10 |
        | 3       | relu      | 1                       | 10    | [[1] * 3] * 10                  |
        | 3       | relu      | 1.1                     | 10    | [[1.1] * 3] * 10                |
        | 3       | relu      | -2                      | 10    | [[0] * 3] * 10                  |
        | 3       | relu      | -2.1                    | 10    | [[0] * 3] * 10                  |
        | 3       | relu      | [[0, 3.4],[-1234,1234]] | 10    | [[[[0,3.4],[0,1234]]] * 3] * 10 |



    Scenario Outline: Shamir Zigmoid
        Given <players> players
        And unary operation shamir <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a                       | count | result                          |
        | 4       | zigmoid   | 1                       | 10    | [[1] * 4] * 10                  |
        | 4       | zigmoid   | 1.1                     | 10    | [[1] * 4] * 10                  |
        | 4       | zigmoid   | -2                      | 10    | [[0] * 4] * 10                  |
        | 4       | zigmoid   | -2.1                    | 10    | [[0] * 4] * 10                  |
        | 4       | zigmoid   | 0.25                    | 10    | [[.75] * 4] * 10                |
        | 4       | zigmoid   | 0.75                    | 10    | [[1] * 4] * 10                  |
        | 4       | zigmoid   | -.0625                  | 10    | [[.4375] * 4] * 10              |
        | 4       | zigmoid   | -.5                     | 10    | [[0] * 4] * 10                  |
        | 4       | zigmoid   | [[0, 3.4],[-1234,1234]] | 10    | [[[[0.5,1],[0,1]]] * 4] * 10 |
        | 3       | zigmoid   | 1                       | 10    | [[1] * 3] * 10                  |
        | 3       | zigmoid   | 1.1                     | 10    | [[1] * 3] * 10                |
        | 3       | zigmoid   | -2                      | 10    | [[0] * 3] * 10                  |
        | 3       | zigmoid   | -2.1                    | 10    | [[0] * 3] * 10                  |
        | 3       | zigmoid   | 0.25                    | 10    | [[.75] * 3] * 10                |
        | 3       | zigmoid   | 0.75                    | 10    | [[1] * 3] * 10                  |
        | 3       | zigmoid   | -.0625                  | 10    | [[.4375] * 3] * 10              |
        | 3       | zigmoid   | -.5                     | 10    | [[0] * 3] * 10                  |
        | 3       | zigmoid   | [[0, 3.4],[-1234,1234]] | 10    | [[[[0.5,1],[0,1]]] * 3] * 10 |

    Scenario Outline: Shamir Private Public Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs private public subtraction on the shamir shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 5       | 5       | 1           | 1      | [4] * 5                                   |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |


    Scenario Outline: Shamir Logical AND
        Given <players> players
        And binary operation shamir logical_and
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 0              | 10    | [[0] * 3] * 10                  |
        | 3        | 0             | 1              | 10    | [[0] * 3] * 10                  |
        | 3        | 1             | 0              | 10    | [[0] * 3] * 10                  |
        | 3        | 1             | 1              | 10    | [[1] * 3] * 10                  |


    Scenario Outline: Shamir Private Public Power
        Given <players> players
        And binary operation shamir private_public_power
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 5              | 10    | [[0] * 3] * 10                  |
        | 3        | 1             | 5              | 10    | [[1] * 3] * 10                  |
        | 3        | 2             | 16             | 10    | [[65536] * 3] * 10              |
        | 3        | -1            | 4              | 10    | [[1] * 3] * 10                  |
        | 3        | -2            | 16             | 10    | [[65536] * 3] * 10              |
        | 3        | -1            | 5              | 10    | [[-1] * 3] * 10                 |

        Examples:
        | players  | a                      | b  | count | result                                              |
        | 3        | [-1, 2, 3.75, -2.0625] | 3  | 10    | [[[-1, 8, 52.734375, -8.773681640625]] * 3] * 10    |



    Scenario Outline: Shamir Private Divide
        Given <players> players
        And binary operation shamir untruncated_private_divide
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result> to within 3 digits

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 5              | 10    | [[0] * 3] * 10                  |
        | 3        | 1             | 5              | 10    | [[.2] * 3] * 10                 |
        | 3        | 2             | 16             | 10    | [[1/8] * 3] * 10                |
        | 3        | 37            | 1              | 10    | [[37.0] * 3] * 10               |
        | 3        | -1            | 5              | 10    | [[-.2] * 3] * 10                |
        | 3        | 2             | -16            | 10    | [[-1/8] * 3] * 10               |
        | 3        | -37           | 1              | 10    | [[-37.0] * 3] * 10              |
