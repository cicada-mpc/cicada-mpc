Feature: Additive Protocol

    Scenario Outline: Startup Reliability
        Given <players> players
        Then it should be possible to setup an additive protocol object <count> times

        Examples:
        | players | count   |
        | 2       | 10      |
        | 3       | 10      |
        | 4       | 10      |
        | 10      | 10      |


    Scenario: Inter-session Repetition
        Given 3 players
        When secret sharing the same value for 10 sessions
	    Then the shares should never be repeated


	Scenario: Intra-session Repetition
        Given 3 players
        When secret sharing the same value 10 times in one session
        Then the shares should never be repeated


    Scenario Outline: Random Round Trip Sharing
        Given <players> players
        When player <player> shares and reveals <count> random secrets, the revealed secrets should match the originals

        Examples:
        | players | player | count      |
        | 2       | 0      | 10         |
        | 3       | 1      | 10         |
        | 4       | 2      | 10         |


    Scenario Outline: Local Addition
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place addition on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                 |
        | 2       | 5       | 1           | 1      | [6] * 2                                |
        | 3       | 5       | 1.1         | 1      | [6.1] * 3                              |
        | 4       | 5       | 1.5         | 2      | [6.5] * 4                              |
        | 3       | [5, 3]  | [1.1, 2.2]  | 1      | [[6.1, 5.2]] * 3                       |


    Scenario Outline: Local Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs local in-place subtraction on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 2       | 5       | 1           | 1      | [4] * 2                                   |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |


    Scenario Outline: Addition
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation               | a          | b          | count |  result             |
        | 2       | public-private addition | -2         | -3.5       | 1     | [[-5.5] * 2]        |
        | 2       | public-private addition | -20        | -30        | 1     | [[-50] * 2]         |
        | 2       | public-private addition | -200       | -300       | 1     | [[-500] * 2]        |
        | 2       | public-private addition | -2000      | -3000      | 1     | [[-5000] * 2]       |
        | 3       | public-private addition | -20000     | -30000     | 1     | [[-50000] * 3]      |
        | 3       | public-private addition | -200000    | -300000    | 1     | [[-500000] * 3]     |
        | 3       | public-private addition | -2000000   | -3000000   | 1     | [[-5000000] * 3]    |
        | 3       | public-private addition | -20000000  | -30000000  | 1     | [[-50000000] * 3]   |
        | 3       | public-private addition | -200000000 | -300000000 | 1     | [[-500000000] * 3]  |
        | 3       | public-private addition | -21        | -35        | 1     | [[-56] * 3]         |
        | 3       | public-private addition | -212       | -351       | 1     | [[-563] * 3]        |
        | 3       | public-private addition | -2123      | -3512      | 1     | [[-5635] * 3]       |
        | 3       | public-private addition | -21234     | -35123     | 1     | [[-56357] * 3]      |
        | 3       | public-private addition | -212345    | -351234    | 1     | [[-563579] * 3]     |
        | 3       | public-private addition | -2123456   | -3512345   | 1     | [[-5635801] * 3]    |
        | 3       | public-private addition | -21234567  | -35123458  | 1     | [[-56358025] * 3]   |
        | 3       | public-private addition | -212345678 | -351234589 | 1     | [[-563580267] * 3]  |

        | 2       | private-private addition | -2         | -3.5      | 1     | [[-5.5] * 2]         |
        | 2       | private-private addition | -20        | -30       | 1     | [[-50] * 2]          |
        | 2       | private-private addition | -200       | -300      | 1     | [[-500] * 2]         |
        | 2       | private-private addition | -2000      | -3000     | 1     | [[-5000] * 2]        |
        | 3       | private-private addition | -20000     | -30000    | 1     | [[-50000] * 3]       |
        | 3       | private-private addition | -200000    | -300000   | 1     | [[-500000] * 3]      |
        | 3       | private-private addition | -2000000   | -3000000  | 1     | [[-5000000] * 3]     |
        | 3       | private-private addition | -20000000  | -30000000 | 1     | [[-50000000] * 3]    |
        | 3       | private-private addition | -200000000 | -300000000| 1     | [[-500000000] * 3]   |
        | 3       | private-private addition | -21        | -35       | 1     | [[-56] * 3]          |
        | 3       | private-private addition | -212       | -351      | 1     | [[-563] * 3]         |
        | 3       | private-private addition | -2123      | -3512     | 1     | [[-5635] * 3]        |
        | 3       | private-private addition | -21234     | -35123    | 1     | [[-56357] * 3]       |
        | 3       | private-private addition | -212345    | -351234   | 1     | [[-563579] * 3]      |
        | 3       | private-private addition | -2123456   | -3512345  | 1     | [[-5635801] * 3]     |
        | 3       | private-private addition | -21234567  | -35123458 | 1     | [[-56358025] * 3]    |
        | 3       | private-private addition | -212345678 | -351234589| 1     | [[-563580267] * 3]   |

    Scenario Outline: Untruncated Multiplication
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                                  | a   | b    | count | result                |
        | 2       | private-private untruncated multiplication | 5   | 2    | 1     | [[655360] * 2]            |
        | 2       | private-private untruncated multiplication | 5   | 2.5  | 1     | [[819200] * 2]          |
        | 2       | private-private untruncated multiplication | 5   | -2.5 | 1     | [[-819200] * 2]         |
        | 2       | private-private untruncated multiplication | -5  | -2.5 | 1     | [[819200] * 2]          |
        | 2       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 1 | [[[655360, 917504]]*2]|
        | 3       | private-private untruncated multiplication | 5   | 2    | 1     | [[655360] * 3]            |
        | 3       | private-private untruncated multiplication | 5   | 2.5  | 1     | [[819200] * 3]          |
        | 3       | private-private untruncated multiplication | 5   | -2.5 | 1     | [[-819200] * 3]         |
        | 3       | private-private untruncated multiplication | -5  | -2.5 | 1     | [[819200] * 3]          |
        | 3       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 1| [[[655360, 917504]]*3] |
        | 4       | private-private untruncated multiplication | 5   | 2    | 1     | [[655360] * 4]            |
        | 4       | private-private untruncated multiplication | 5   | 2.5  | 1     | [[819200] * 4]          |
        | 4       | private-private untruncated multiplication | 5   | -2.5 | 1     | [[-819200] * 4]         |
        | 4       | private-private untruncated multiplication | -5  | -2.5 | 1     | [[819200] * 4]          |
        | 4       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 1|[[[655360, 917504]]*4]|
        | 5       | private-private untruncated multiplication | 5   | 2    | 1     | [[655360] * 5]            |
        | 5       | private-private untruncated multiplication | 5   | 2.5  | 1     | [[819200] * 5]          |
        | 5       | private-private untruncated multiplication | 5   | -2.5 | 1     | [[-819200] * 5]         |
        | 5       | private-private untruncated multiplication | -5  | -2.5 | 1     | [[819200] * 5]          |
        | 5       | private-private untruncated multiplication | [5, 3.5] | [2, 4]  | 1|[[[655360, 917504]]*5] |


    Scenario Outline: Logical Exclusive Or
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation           | a      | b      | count | result             |
        | 2       | private-private xor | 0      | 0      | 1     | [[0] * 2]          |
        | 2       | private-private xor | 0      | 1      | 1     | [[1] * 2]          |
        | 2       | private-private xor | 1      | 0      | 1     | [[1] * 2]          |
        | 2       | private-private xor | 1      | 1      | 1     | [[0] * 2]          |


    Scenario Outline: Logical Or
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation          | a      | b      | count | result             |
        | 2       | private-private or | 0      | 0      | 1     | [[0] * 2]          |
        | 2       | private-private or | 0      | 1      | 1     | [[1] * 2]          |
        | 2       | private-private or | 1      | 0      | 1     | [[1] * 2]          |
        | 2       | private-private or | 1      | 1      | 1     | [[1] * 2]          |


    Scenario Outline: Max
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a              | b                  | count | result                         |
        | 3       | max       | 2              | 3.5                | 1     | [[3.5] * 3]                    |
        | 3       | max       | 3.5            | 2                  | 1     | [[3.5] * 3]                    |
        | 3       | max       | -3             | 2                  | 1     | [[2] * 3]                      |
        | 3       | max       | 2              | -3                 | 1     | [[2] * 3]                      |
        | 3       | max       | -4             | -3                 | 1     | [[-3] * 3]                     |
        | 3       | max       | [2, 3, -2, -1] | [3.5, 1, 1, -4]    | 1     | [[[3.5, 3, 1, -1]] * 3]        |


    Scenario Outline: Min
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a              | b                  | count | result                         |
        | 3       | min       | 2              | 3.5                | 1     | [[2] * 3]                      |
        | 3       | min       | 3.5            | 2                  | 1     | [[2] * 3]                      |
        | 3       | min       | -3             | 2                  | 1     | [[-3] * 3]                     |
        | 3       | min       | 2              | -3                 | 1     | [[-3] * 3]                     |
        | 3       | min       | -4             | -3                 | 1     | [[-4] * 3]                     |
        | 3       | min       | [2, 3, -2, -1] | [3.5, 1, -2, -4]   | 1     | [[[2, 1, -2, -4]] * 3]         |


    Scenario Outline: Random Bitwise Secret
        Given <players> players
        Then generating <bits> random bits with players <src> and seed <seed> produces a valid result

        Examples:
        | players | bits  | src       | seed |
        | 2       | 1     | None      | 1234 |
        | 2       | 2     | None      | 1235 |
        | 2       | 4     | None      | 1236 |
        | 2       | 8     | None      | 1237 |
        | 3       | 8     | None      | 1238 |
        | 3       | 8     | None      | 1239 |


    Scenario Outline: Multiplication
        Given <players> players
        And binary operation <operation>
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation                      | a   | b    | count | result                |
        | 2       | private-private multiplication | 5   | 2    | 1     | [[10] * 2]            |
        | 2       | private-private multiplication | 5   | 2.5  | 1     | [[12.5] * 2]          |
        | 2       | private-private multiplication | 5   | -2.5 | 1     | [[-12.5] * 2]         |
        | 2       | private-private multiplication | -5  | -2.5 | 1     | [[12.5] * 2]          |
        | 2       | private-private multiplication | [5, 3.5]   | [2, 4]  | 1     | [[[10, 14]] * 2]            |
        | 3       | private-private multiplication | 5   | 2    | 1     | [[10] * 3]            |
        | 3       | private-private multiplication | 5   | 2.5  | 1     | [[12.5] * 3]          |
        | 3       | private-private multiplication | 5   | -2.5 | 1     | [[-12.5] * 3]         |
        | 3       | private-private multiplication | -5  | -2.5 | 1     | [[12.5] * 3]          |
        | 3       | private-private multiplication | [5, 3.5]   | [2, 4]  | 1     | [[[10, 14]] * 3]            |
        | 4       | private-private multiplication | 5   | 2    | 1     | [[10] * 4]            |
        | 4       | private-private multiplication | 5   | 2.5  | 1     | [[12.5] * 4]          |
        | 4       | private-private multiplication | 5   | -2.5 | 1     | [[-12.5] * 4]         |
        | 4       | private-private multiplication | -5  | -2.5 | 1     | [[12.5] * 4]          |
        | 4       | private-private multiplication | [5, 3.5]   | [2, 4]  | 1     | [[[10, 14]] * 4]            |
        | 5       | private-private multiplication | 5   | 2    | 1     | [[10] * 5]            |
        | 5       | private-private multiplication | 5   | 2.5  | 1     | [[12.5] * 5]          |
        | 5       | private-private multiplication | 5   | -2.5 | 1     | [[-12.5] * 5]         |
        | 5       | private-private multiplication | -5  | -2.5 | 1     | [[12.5] * 5]          |
        | 5       | private-private multiplication | [5, 3.5]   | [2, 4]  | 1     | [[[10, 14]] * 5]            |


    Scenario Outline: Floor
        Given <players> players
        And unary operation <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a             | count | result               |
        | 2       | floor     | 1             | 1     | [[1] * 2]            |
        | 2       | floor     | 1.1           | 1     | [[1] * 2]            |
        | 2       | floor     | -2            | 1     | [[-2] * 2]           |
        | 2       | floor     | -2.1          | 1     | [[-3] * 2]           |
        | 2       | floor     | [1.2, -3.4]   | 1     | [[[1, -4]] * 2]      |
        | 3       | floor     | 1             | 1     | [[1] * 3]            |
        | 3       | floor     | 1.1           | 1     | [[1] * 3]            |
        | 3       | floor     | -2            | 1     | [[-2] * 3]           |
        | 3       | floor     | -2.1          | 1     | [[-3] * 3]           |
        | 3       | floor     | [1.2, -3.4]   | 1     | [[[1, -4]] * 3]      |


    Scenario Outline: Equality
        Given <players> players
        And binary operation private-private equality
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a                 | b                | count | result                        |
        | 2        | 2                 | 2                | 1     | [[1] * 2]                     |
        | 2        | 2                 | 3                | 1     | [[0] * 2]                     |
        | 2        | 2                 | 2.1              | 1     | [[0] * 2]                     |
        | 2        | 2.1               | 2.1              | 1     | [[1] * 2]                     |
        | 2        | -2                | -2               | 1     | [[1] * 2]                     |
        | 2        | -2                | -3               | 1     | [[0] * 2]                     |
        | 2        | -2                | -2.1             | 1     | [[0] * 2]                     |
        | 2        | -2.1              | -2.1             | 1     | [[1] * 2]                     |
        | 2        | -2                | 2                | 1     | [[0] * 2]                     |
        | 3        | [1, -2, 3, -4.5]  | [1, 2, 3, -4.5]  | 1     | [[[1,0,1,1]] * 3]             |


    @wip
    Scenario Outline: Modulus
        Given <players> players
        And binary operation private-public modulus
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a                 | b                | count | result                          |
        | 3        | 144409            | 117              | 1     | [[144409 % 117] * 2]            |
        | 3        | 144409            | 118              | 1     | [[144409 % 118] * 2]            |
        | 3        | 144409            | 119              | 1     | [[144409 % 119] * 2]            |
        | 3        | 144409            | 120              | 1     | [[144409 % 120] * 2]            |
        | 3        | 144409            | 121              | 1     | [[144409 % 121] * 2]            |
        | 3        | 144409            | 122              | 1     | [[144409 % 122] * 2]            |
        | 3        | 144409            | 123              | 1     | [[144409 % 123] * 2]            |
        | 3        | 144409            | 124              | 1     | [[144409 % 124] * 2]            |
        | 3        | 144409            | 125              | 1     | [[144409 % 125] * 2]            |
        | 3        | 144409            | 126              | 1     | [[144409 % 126] * 2]            |

    Scenario Outline: Multiplicative Inverse
        Given <players> players
        And unary operation <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation             | a                                | count| result                |
        | 2       | multiplicative_inverse| 2                                | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| 100                              | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| -75                              | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| -1000                            | 1    | [[1] * 2]             |
        | 2       | multiplicative_inverse| [[35.125,65.25],[73.5, -3.0625]] | 1    | [[[[1,1],[1,1]]] * 2] |
        | 3       | multiplicative_inverse| 2                                | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| 100                              | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| -75                              | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| -1000                            | 1    | [[1] * 3]             |
        | 3       | multiplicative_inverse| [[35.125,65.25],[73.5, -3.0625]] | 1    | [[[[1,1],[1,1]]] * 3] |


    Scenario Outline: Less
        Given <players> players
        And binary operation less 
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 0              | 1     | [[0] * 3]                       |
        | 3        | 0             | 100            | 1     | [[1] * 3]                       |
        | 3        | 0             | -100           | 1     | [[0] * 3]                       |
        | 3        | 0             | 2**-16         | 1     | [[1] * 3]                       |
        | 3        | 0             | -2**-16        | 1     | [[0] * 3]                       |
        | 3        | -100          | 100            | 1     | [[1] * 3]                       |
        | 3        | 100           | 100            | 1     | [[0] * 3]                       |
        | 3        | -100          | -100           | 1     | [[0] * 3]                       |
        | 3        | 2**16         | 2**16-1        | 1     | [[0] * 3]                       |
        | 3        | 2**16-2       | 2**16-1        | 1     | [[1] * 3]                       |
        | 3        | [[1,2],[3,4]] | [[2,2],[4,4]]  | 1     | [[[[1,0],[1,0]]] * 3]           |


    Scenario Outline: ReLU 
        Given <players> players
        And unary operation <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a                       | count | result                          |
        | 2       | relu      | 1                       | 1     | [[1] * 2]                       |
        | 2       | relu      | 1.1                     | 1     | [[1.1] * 2]                     |
        | 2       | relu      | -2                      | 1     | [[0] * 2]                       |
        | 2       | relu      | -2.1                    | 1     | [[0] * 2]                       |
        | 2       | relu      | [[0, 3.4],[-1234,1234]] | 1     | [[[[0,3.4],[0,1234]]] * 2]      |
        | 3       | relu      | 1                       | 1     | [[1] * 3]                       |
        | 3       | relu      | 1.1                     | 1     | [[1.1] * 3]                     |
        | 3       | relu      | -2                      | 1     | [[0] * 3]                       |
        | 3       | relu      | -2.1                    | 1     | [[0] * 3]                       |
        | 3       | relu      | [[0, 3.4],[-1234,1234]] | 1     | [[[[0,3.4],[0,1234]]] * 3]      |



    Scenario Outline: Zigmoid
        Given <players> players
        And unary operation <operation>
        And operand <a>
        When the unary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players | operation | a                       | count | result                          |
        | 2       | zigmoid   | 1                       | 1     | [[1] * 2]                       |
        | 2       | zigmoid   | 1.1                     | 1     | [[1] * 2]                       |
        | 2       | zigmoid   | -2                      | 1     | [[0] * 2]                       |
        | 2       | zigmoid   | -2.1                    | 1     | [[0] * 2]                       |
        | 2       | zigmoid   | 0.25                    | 1     | [[.75] * 2]                     |
        | 2       | zigmoid   | 0.75                    | 1     | [[1] * 2]                       |
        | 2       | zigmoid   | -.0625                  | 1     | [[.4375] * 2]                   |
        | 2       | zigmoid   | -.5                     | 1     | [[0] * 2]                       |
        | 2       | zigmoid   | [[0, 3.4],[-1234,1234]] | 1     | [[[[0.5,1],[0,1]]] * 2]         |
        | 3       | zigmoid   | 1                       | 1     | [[1] * 3]                       |
        | 3       | zigmoid   | 1.1                     | 1     | [[1] * 3]                       |
        | 3       | zigmoid   | -2                      | 1     | [[0] * 3]                       |
        | 3       | zigmoid   | -2.1                    | 1     | [[0] * 3]                       |
        | 3       | zigmoid   | 0.25                    | 1     | [[.75] * 3]                     |
        | 3       | zigmoid   | 0.75                    | 1     | [[1] * 3]                       |
        | 3       | zigmoid   | -.0625                  | 1     | [[.4375] * 3]                   |
        | 3       | zigmoid   | -.5                     | 1     | [[0] * 3]                       |
        | 3       | zigmoid   | [[0, 3.4],[-1234,1234]] | 1     | [[[[0.5,1],[0,1]]] * 3]         |

    Scenario Outline: Private Public Subtraction
        Given <players> players
        And secret value <secret>
        And local value <local>
        When player <player> performs private public subtraction on the shared secret
        Then the group should return <result>

        Examples:
        | players | secret  | local       | player | result                                    |
        | 2       | 5       | 1           | 1      | [4] * 2                                   |
        | 3       | 5       | 1.1         | 1      | [3.9] * 3                                 |
        | 4       | 5       | 1.5         | 1      | [3.5] * 4                                 |
        | 3       | [5, 3]  | [1.1, 3.2]  | 1      | [[3.9, -0.2]] * 3                         |


    Scenario Outline: Logical AND
        Given <players> players
        And binary operation logical_and
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 0              | 1     | [[0] * 3]                       |
        | 3        | 0             | 1              | 1     | [[0] * 3]                       |
        | 3        | 1             | 0              | 1     | [[0] * 3]                       |
        | 3        | 1             | 1              | 1     | [[1] * 3]                       |


    Scenario Outline: Private Public Power
        Given <players> players
        And binary operation private_public_power
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result>

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 5              | 1     | [[0] * 3]                       |
        | 3        | 1             | 5              | 1     | [[1] * 3]                       |
        | 3        | 2             | 16             | 1     | [[65536] * 3]                   |
        | 3        | -1            | 4              | 1     | [[1] * 3]                       |
        | 3        | -2            | 16             | 1     | [[65536] * 3]                   |
        | 3        | -1            | 5              | 1     | [[-1] * 3]                      |

        Examples:
        | players  | a                      | b  | count | result                                              |
        | 3        | [-1, 2, 3.75, -2.0625] | 3  | 1     | [[[-1, 8, 52.734375, -8.773681640625]] * 3]         |



    Scenario Outline: Private Divide
        Given <players> players
        And binary operation untruncated_private_divide
        And operands <a> and <b>
        When the binary operation is executed <count> times
        Then the group should return <result> to within 3 digits

        Examples:
        | players  | a             | b              | count | result                          |
        | 3        | 0             | 5              | 1     | [[0] * 3]                       |
        | 3        | 1             | 5              | 1     | [[.2] * 3]                      |
        | 3        | 2             | 16             | 1     | [[1/8] * 3]                     |
        | 3        | 37            | 1              | 1     | [[37.0] * 3]                    |
        | 3        | -1            | 5              | 1     | [[-.2] * 3]                     |
        | 3        | 2             | -16            | 1     | [[-1/8] * 3]                    |
        | 3        | -37           | 1              | 1     | [[-37.0] * 3]                   |
