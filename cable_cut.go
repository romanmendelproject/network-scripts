package main

import (
    "bufio"
    "fmt"
    g "github.com/soniah/gosnmp"
    "log"
    "os"
    "strconv"
    "sync"
    "time"
)

const len_delta int = 5

type SwitchStruct struct {
    ipsw        string
    status_pair []int
    pair1status []int
    pair1len    []int
}

func snmpget(SWData SwitchStruct, mu *sync.Mutex) {

    envTarget := SWData.ipsw
    envPort := "161"
    if len(envTarget) <= 0 {
        log.Fatalf("environment variable not set: GOSNMP_TARGET")
    }
    if len(envPort) <= 0 {
        log.Fatalf("environment variable not set: GOSNMP_PORT")
    }
    port, _ := strconv.ParseUint(envPort, 10, 16)
    params := &g.GoSNMP{
        Target:    envTarget,
        Port:      uint16(port),
        Community: "password",
        Version:   g.Version2c,
        Timeout:   time.Duration(2) * time.Second,
        Logger:    log.New(os.Stdout, "", 0),
    }
    err := params.Connect()

    if err != nil {
        log.Println("Get() err: %v", err)
        return
    }
    defer params.Conn.Close()

    oids := []string{"1.3.6.1.2.1.2.2.1.8"}
    result2, err2 := params.GetBulk(oids, 0, 24)
    if err2 != nil {
        log.Println("Get() err: %v", err2)
        return
    }
    for i := 0; i < 24; i++ {
        mu.Lock()
        SWData.status_pair[i] = result2.Variables[i].Value.(int)
        mu.Unlock()
        if result2.Variables[i].Value.(int) == 2 {
            fmt.Println("!!!!!!!!!!!!!%v", i)
            oid := "1.3.6.1.4.1.171.12.58.1.1.1." + strconv.Itoa(i+1)
            var pdus []g.SnmpPDU
            pdus = append(pdus, g.SnmpPDU{oid, 0x02, 1, nil})
            _, err2 := params.Set(pdus)
            if err2 != nil {
                log.Println("Get() err: %v", err2)
                return
            }
        }
    }
    oids = []string{"1.3.6.1.4.1.171.12.58.1.1.1.4", "1.3.6.1.4.1.171.12.58.1.1.1.8"}
    result, err2 := params.GetBulk(oids, 0, 24)
    if err2 != nil {
        log.Println("Get() err: %v", err2)
        return
    }

    j := 0
    for i := 0; i < 48; i += 2 {
        mu.Lock()
        SWData.pair1status[j] = result.Variables[i].Value.(int)
        mu.Unlock()
        j++
    }

    j = 0
    for i := 1; i < 48; i += 2 {
        if result2.Variables[j].Value.(int) == 2 && result.Variables[i-1].Value.(int) == 1 {
            mu.Lock()
            cable_delta_item := SWData.pair1len[j] - result.Variables[i].Value.(int)
            mu.Unlock()
            if cable_delta_item > len_delta {
                log.Println("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!! %v", cable_delta_item)
            }

        }
        mu.Lock()
        SWData.pair1len[j] = result.Variables[i].Value.(int)
        mu.Unlock()
        j++
    }
    mu.Lock()
    log.Println(SWData)
    mu.Unlock()
}

func main() {
    f, err := os.OpenFile("testlogfile", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
    if err != nil {
        log.Fatalf("error opening file: %v", err)
    }
    defer f.Close()
    log.SetOutput(f)
    mu := &sync.Mutex{}
    swips := []string{"10.0.0.1", "10.0.0.2", "10.0.0.3"}
    SWData := make([]SwitchStruct, len(swips))
    for i, ip := range swips {
        SWData[i] = SwitchStruct{ip, make([]int, 24), make([]int, 24), make([]int, 24)}
    }
LOOP:
    for i := 0; i < len(swips); i++ {
        go snmpget(SWData[i], mu)
        if i == len(swips)-1 {
            time.Sleep(2 * time.Second)
            goto LOOP
        }
    }
    bufio.NewReader(os.Stdin).ReadBytes('\n')
    fmt.Println(SWData)

}
