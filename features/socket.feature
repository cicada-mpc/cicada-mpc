Feature: SocketCommunicator

    Scenario: Barrier
        Given 3 players
        When the players enter a barrier at different times
        Then the players should exit the barrier at roughly the same time


    Scenario Outline: Allgather
        Given <players> players
        When the players allgather <values>
        Then the group should return <result>

        Examples:
        | players | values             | result             |
        | 2       | [0, 1]             | [[0, 1]] * 2       |
        | 3       | [1, 2, "c"]        | [[1, 2, "c"]] * 3  |


    Scenario Outline: Asynchronous Send
        Given <players> players
        When player <source> asynchronously sends <value> to player <destination>
        Then the group should return <result>

        Examples:
        | players | source | value | destination | result              |
        | 3       | 1      | "foo" | 2           | [None, None, "foo"] |


    Scenario Outline: Asynchronous Send and Wait
        Given <players> players
        When player <source> asynchronously sends <value> to player <destination> who waits
        Then the group should return <result>

        Examples:
        | players | source | value | destination | result              |
        | 3       | 1      | "bar" | 2           | [None, None, "bar"] |


    Scenario Outline: Broadcast
        Given <players> players
        When player <src> broadcasts <value>
        Then the group should return <result>

        Examples:
        | players | src      | value   | result             |
        | 2       | 0        | 1.23    | [1.23, 1.23]       |
        | 2       | 1        | 2.34    | [2.34, 2.34]       |
        | 3       | 1        | 4.02    | [4.02, 4.02, 4.02] |


    Scenario Outline: Connect
        Given <players> players
        When the players create a new communicator with connect.
        Then the group should return <result>

        Examples:
        | players | result      |
        | 2       | [None] * 2  |
        | 3       | [None] * 3  |
        | 10      | [None] * 10 |


    Scenario Outline: Environment Connect
        Given <players> players
        When the players create a new communicator with connect using environment variables.
        Then the group should return <result>

        Examples:
        | players | result      |
        | 2       | [None] * 2  |
        | 3       | [None] * 3  |
        | 10      | [None] * 10 |


    Scenario Outline: Environment Connect With TLS
        Given <players> players
        When the players create a new communicator with connect using environment variables and tls.
        Then the group should return <result>

        Examples:
        | players | result      |
        | 2       | [None] * 2  |
        | 3       | [None] * 3  |
        | 10      | [None] * 10 |


    Scenario Outline: Failure Recovery
        Given <players> players
        When player <slacker> fails and the others revoke and shrink the communicator, the new communicator should include the remaining players

        Examples:
        | players | slacker |
        | 2       | 0       |
        | 2       | 1       |
        | 4       | 0       |
        | 4       | 2       |
        | 8       | 6       |


    Scenario: Freed Communicator
        Given 3 players
        When player 1 broadcasts 1.23 after the communicator has been freed
        Then players range(3) should fail with NotRunning errors


    Scenario Outline: Gather
        Given <players> players
        When player <dst> gathers <values>
        Then the group result should equal <result>

        Examples:
        | players | dst  | values      | result                        |
        | 2       | 0    | [2, 3]      | [[2, 3], None]                |
        | 2       | 1    | [3, 4.1]    | [None, [3, 4.1]]              |
        | 3       | 1    | [1, 2, 3.2] | [None, [1, 2, 3.2], None]     |
        | 3       | 2    | [2, 3, 1.1] | [None, None, [2, 3, 1.1]]     |


    Scenario Outline: GatherV
        Given <players> players
        When player <dst> gathers <values> from <sources>
        Then the group result should equal <result>

        Examples:
        | players | dst  | values             | sources      | result                        |
        | 3       | 0    | [0, 1, 2]          | [1, 2]       | [[1, 2], None, None]          |
        | 3       | 1    | [0, 1, 2]          | [0, 2]       | [None, [0, 2], None]          |
        | 4       | 1    | [0, 1, 2, 3]       | [0, 2, 3]    | [None, [0, 2, 3], None, None] |
        | 4       | 1    | [0, 1, 2, 3]       | [2, 0, 3]    | [None, [2, 0, 3], None, None] |


    Scenario Outline: Message Reliability
        Given <players> players
        When player <src> scatters messages to the other players <count> times
        Then player <src> should have sent exactly <sent> messages
        And every player other than <src> should receive exactly <received> messages

        Examples:
        | players | src       | count   | sent    | received           |
        | 2       | 0         | 100     | 101     | [101]              |
        | 3       | 0         | 100     | 202     | [102, 102]         |
        | 2       | 0         | 1000    | 1001    | [1001]             |
        | 3       | 0         | 1000    | 2002    | [1002, 1002]       |
        | 2       | 0         | 10000   | 10001   | [10001]            |
        | 3       | 0         | 10000   | 20002   | [10002, 10002]     |
        | 2       | 0         | 100000  | 100001  | [100001]           |
        | 3       | 0         | 100000  | 200002  | [100002, 100002]   |


    Scenario Outline: New Communicator
        Given <players> players
        When players <group> create a new communicator with world size <world_size> and name <name> and token <token>
        Then the new communicator names should match <names>
        And the new communicator world sizes should match <world_sizes>

        Examples:
        | players | group           | world_size | name     | token           | names          | world_sizes |
        | 2       | range(2)        | 2          | "red"    | 13              | ["red"] * 2    | [2] * 2     |
        | 3       | range(3)        | 3          | "green"  | "token"         | ["green"] * 3  | [3] * 3     |
        | 10      | range(10)       | 10         | "blue"   | "OurSecretClub" | ["blue"] * 10  | [10] * 10   |


    Scenario Outline: New Communicator Missing Players
        Given <players> players
        When players <group> create a new communicator with world size <world_size> and name "foo" and token "bar"
        Then players <group> should timeout

        Examples:
        | players | group          | world_size |
        | 2       | [0]            | 2          |
        | 2       | [1]            | 2          |
        | 3       | [0, 1]         | 3          |
        | 3       | [1, 2]         | 3          |
        | 10      | range(0, 9)    | 10         |
        | 10      | range(1, 10)   | 10         |


    Scenario Outline: New Communicator Token Mismatch
        Given <players> players
        When players <group> create a new communicator with world size <world_size> and name "foo" and tokens <tokens>
        Then players <group> should fail with TokenMismatch errors

        Examples:
        | players | group       | world_size | tokens                        |
        | 2       | range(2)    | 2          | [3, "3"]                      |
        | 3       | range(3)    | 3          | ["foo", "bar", "baz"]         |
        | 10      | range(10)   | 10         | list(range(9)) + ["blah"]     |


    Scenario Outline: Predefined Communicator
        Given <players> players
        When players <group> create a new communicator with name <name> and direct addresses <addresses>
        Then the new communicator names should match <names>
        And the new communicator world sizes should match <world_sizes>

        @wip
        Examples:
        | players | group        | name       | addresses                                          | names        | world_sizes   |
        | 2       | range(2)     | "red"      | ["tcp://127.0.0.1:34000", "tcp://127.0.0.1:34001"] | ["red"] * 2  | [2] * 2       |

        Examples:
        | players | group        | name       | addresses                                          | names        | world_sizes   |
        | 2       | range(2)     | "blue"     | ["file:///tmp/cicada0", "file:///tmp/cicada1"]     | ["blue"] * 2 | [2] * 2       |


    Scenario Outline: Revoke Communicator
        Given <players> players
        When player <player> revokes the communicator
        Then players <group> should fail with Revoked errors

        Examples:
        | players | player | group       |
        | 2       | 0      | range(2)    |
        | 2       | 1      | range(2)    |
        | 3       | 0      | range(3)    |
        | 3       | 1      | range(3)    |
        | 3       | 2      | range(3)    |
        | 10      | 8      | range(10)   |
        | 32      | 11     | range(32)   |


    Scenario Outline: Scatter
        Given <players> players
        When player <src> scatters <values>
        Then the group should return <result>

        Examples:
        | players | src  | values      | result          |
        | 2       | 0    | [2, 3]      | [2, 3]          |
        | 2       | 1    | [3, 4.1]    | [3, 4.1]        |
        | 3       | 1    | [1, 2, 3.2] | [1, 2, 3.2]     |
        | 3       | 2    | [2, 3, 1.1] | [2, 3, 1.1]     |


    Scenario Outline: ScatterV
        Given <players> players
        When player <src> scatters <values> to <destinations>
        Then the group should return <result>

        Examples:
        | players | src  | values      | destinations | result                |
        | 3       | 0    | [2, 3]      | [1, 2]       | [None, 2, 3]          |
        | 3       | 1    | [3, 4.1]    | [0, 2]       | [3, None, 4.1]        |
        | 4       | 1    | [1, 2, 3.2] | [0, 1, 2]    | [1, 2, 3.2, None]     |
        | 4       | 2    | [2, 3, 1.1] | [3, 1, 2]    | [None, 3, 1.1, 2]     |


    Scenario Outline: Send-Receive
        Given <players> players
        Then player <src> can send <value> to player <dest>

        Examples:
        | players | src  | dest    | value   |
        | 2       | 0    | 1       | 1.23    |
        | 2       | 1    | 0       | 2.34    |
        | 3       | 1    | 2       | 4.02    |
        | 3       | 2    | 0       | -55.5   |


    Scenario Outline: Startup Reliability
        Given <players> players
        Then it should be possible to start and stop a communicator <count> times

        Examples:
        | players | count   |
        | 2       | 100     |
        | 3       | 100     |
        | 4       | 100     |
        | 10      | 100     |


    Scenario Outline: Shrink Communicator
        Given <players> players
        And <family> addressing
        When players <group> shrink the communicator with name <name>
        Then the new communicator names should match <names>
        And the new communicator world sizes should match <world_sizes>

        Examples:
        | players | family   | group       | name      | names         | world_sizes |
        | 2       | "tcp"    | range(2)    | "red"     | ["red"] * 2   | [2] * 2     |
        | 3       | "tcp"    | range(3)    | "green"   | ["green"] * 3 | [3] * 3     |
        | 10      | "tcp"    | range(10)   | "blue"    | ["blue"] * 10 | [10] * 10   |
        | 10      | "file"   | range(10)   | "blue"    | ["blue"] * 10 | [10] * 10   |

        @wip
        Examples:
        | players | family   | group       | name    | names                    | world_sizes      |
        | 3       | "tcp"    | [0, 1]      | "red"   | ["red", "red", None]     | [2, 2, None]     |
        | 3       | "tcp"    | [1, 2]      | "red"   | [None, "red", "red"]     | [None, 2, 2]     |


    Scenario Outline: Split Communicator
        Given <players> players
        And <family> addressing
        When the players split the communicator with names <names>
        Then the new communicator names should match <names>
        And the new communicator world sizes should match <world_sizes>

        Examples:
        | players | family   | names                             | world_sizes      |
        | 2       | "tcp"    | ["a", "b"]                        | [1, 1]           |
        | 3       | "tcp"    | ["a", "b", "a"]                   | [2, 1, 2]        |
        | 4       | "tcp"    | ["red", "red", "red", "blue"]     | [3, 3, 3, 1]     |
        | 4       | "tcp"    | ["red", None, "red", "blue"]      | [2, None, 2, 1]  |
        | 4       | "file"   | ["red", None, "red", "blue"]      | [2, None, 2, 1]  |


    Scenario Outline: Permanent Timeout Changes
        Given <players> players
        When the communicator timeout is permanently changed to <timeout>
        Then the initial communicator timeouts should match <initial>
        And the final communicator timeouts should match <final>

        Examples:
        | players | timeout | initial | final    |
        | 3       | 10      | [5] * 3 | [10] * 3 |


    Scenario Outline: Temporary Timeout Changes
        Given <players> players
        When the communicator timeout is temporarily changed to <timeout>
        Then the initial communicator timeouts should match <initial>
        And the temporary communicator timeouts should match <temporary>
        And the final communicator timeouts should match <final>

        Examples:
        | players | timeout | initial | temporary | final   |
        | 3       | 10      | [5] * 3 | [10] * 3  | [5] * 3 |


    Scenario Outline: Trust
        Given <players> players
        When the players create a new communicator with connect, but player <a> doesn't trust player <b>
        Then the group should raise exceptions <result>

        @wip
        Examples:
        | players | a         | b     | result                                         |
        | 2       | 1         | 0     | [EncryptionFailed, EncryptionFailed]           |
        | 3       | 1         | 0     | [EncryptionFailed, EncryptionFailed, Timeout]  |
        | 3       | 1         | 2     | [None, EncryptionFailed, None]                 |
        | 3       | 2         | 1     | [None, EncryptionFailed, EncryptionFailed]     |


        @wip
        Examples:
        | players | a         | b     | result                                         |
        | 2       | 0         | 1     | [EncryptionFailed, EncryptionFailed]           |
        | 3       | 0         | 1     | [EncryptionFailed, EncryptionFailed, Timeout]  |


    Scenario Outline: SocketCommunicator.run Exception Handling

        Given <players> players
        And a startup timeout of 60 seconds
        When every player raises <exception>
        Then SocketCommunicator.run should catch <exception> from every player

        Examples:
        | players  | exception            |
        | 2        | RuntimeError("Doh!") |
        | 4        | RuntimeError("Doh!") |
        | 8        | RuntimeError("Doh!") |
        | 16       | RuntimeError("Doh!") |
        | 32       | RuntimeError("Doh!") |
        | 64       | RuntimeError("Doh!") |

        Examples:
        | players  | exception            |
        | 128      | RuntimeError("Doh!") |

