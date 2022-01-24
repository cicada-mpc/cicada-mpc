Feature: Communication

    Scenario: Barrier
        Given 3 players
        And cicada.communicator.SocketCommunicator
        When the players enter a barrier at different times
        Then the players should exit the barrier at roughly the same time


    Scenario Outline: Broadcast
        Given <players> players
        And cicada.communicator.SocketCommunicator
        When player <src> broadcasts <value>
        Then the group should return <result>

        Examples:
        | players | src      | value   | result             |
        | 2       | 0        | 1.23    | [1.23, 1.23]       |
        | 2       | 1        | 2.34    | [2.34, 2.34]       |
        | 3       | 1        | 4.02    | [4.02, 4.02, 4.02] |


    Scenario Outline: Gather
        Given <players> players
        And cicada.communicator.SocketCommunicator
        When player <dst> gathers <values>
        Then the group should return <result>

        Examples:
        | players | dst  | values      | result                        |
        | 2       | 0    | [2, 3]      | [[2, 3], None]                |
        | 2       | 1    | [3, 4.1]    | [None, [3, 4.1]]              |
        | 3       | 1    | [1, 2, 3.2] | [None, [1, 2, 3.2], None]     |
        | 3       | 2    | [2, 3, 1.1] | [None, None, [2, 3, 1.1]]     |


    Scenario Outline: GatherV
        Given <players> players
        And cicada.communicator.SocketCommunicator
        When player <dst> gathers <values> from <sources>
        Then the group should return <result>

        Examples:
        | players | dst  | values             | sources      | result                        |
        | 3       | 0    | [0, 1, 2]          | [1, 2]       | [[1, 2], None, None]          |
        | 3       | 1    | [0, 1, 2]          | [0, 2]       | [None, [0, 2], None]          |
        | 4       | 1    | [0, 1, 2, 3]       | [0, 2, 3]    | [None, [0, 2, 3], None, None] |
        | 4       | 1    | [0, 1, 2, 3]       | [2, 0, 3]    | [None, [2, 0, 3], None, None] |


    Scenario Outline: Message Reliability
        Given <players> players
        And cicada.communicator.SocketCommunicator
        When player <src> scatters messages to the other players <count> times
        Then player <src> should have sent exactly <sent> messages
        And every player other than <src> should receive exactly <received> messages

        Examples:
        | players | src       | count   | sent    | received |
        | 2       | 0         | 100     | 101     | 101      |
        | 3       | 0         | 100     | 202     | 102      |
        | 2       | 0         | 1000    | 1001    | 1001     |
        | 3       | 0         | 1000    | 2002    | 1002     |
        | 2       | 0         | 10000   | 10001   | 10001    |
        | 3       | 0         | 10000   | 20002   | 10002    |
        | 2       | 0         | 100000  | 100001  | 100001   |
        | 3       | 0         | 100000  | 200002  | 100002   |


    Scenario Outline: Scatter
        Given <players> players
        And cicada.communicator.SocketCommunicator
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
        And cicada.communicator.SocketCommunicator
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
        And cicada.communicator.SocketCommunicator
        Then player <src> can send <value> to player <dest>

        Examples:
        | players | src  | dest    | value   |
        | 2       | 0    | 1       | 1.23    |
        | 2       | 1    | 0       | 2.34    |
        | 3       | 1    | 2       | 4.02    |
        | 3       | 2    | 0       | -55.5   |


    Scenario Outline: Startup Reliability
        Given <players> players
        And cicada.communicator.SocketCommunicator
        Then it should be possible to start and stop a communicator <count> times

        Examples:
        | players | count   |
        | 2       | 100     |
        | 3       | 100     |
        | 4       | 100     |
        | 10      | 100     |


