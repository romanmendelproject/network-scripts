package main

import (
    //  "bufio"
    "encoding/json"
    "fmt"
    g "github.com/soniah/gosnmp"
    "html/template"
    "log"
    "net/http"
    "net/url"
    "os"
    "regexp"
    "strconv"
    //"strings"
    "sync"
    "time"
)

type SwitchStruct struct {
    ipsw        string
    status_pair []int
    pair1status []int
    pair1len    []int
}

func main() {
    fmt.Println("Listening on port :3000")
    http.Handle("/assets/", http.StripPrefix("/assets/", http.FileServer(http.Dir("./assets/"))))
    http.HandleFunc("/receive", receiveAjax)
    http.HandleFunc("/receive2", receiveAjax2)

    http.ListenAndServe(":3000", nil)
}

func swap(a, b string) (string, string) {
    return b, a
}

func receiveAjax(w http.ResponseWriter, r *http.Request) {
    t, err := template.ParseFiles("templates/index2.html", "templates/header.html")
    if err != nil {
        return
    }
    w.Header().Set("Content-Type", "text/html; charset=utf-8")
    w.Header().Set("Access-Control-Allow-Origin", "*")
    t.Execute(w, nil)
}

func receiveAjax2(w http.ResponseWriter, r *http.Request) {
    if r.Method == "POST" {
        address_sw := r.FormValue("sendedData")
        //address_sw_replace := strings.Replace(address_sw, " ", "%20", 5)
        address_sw_replace := url.QueryEscape(address_sw)
        resp, err := http.Get("http://test.ru/cgi-bin/ppo/xml/ertel_xml_reports.p_search_ip_by_address?pr_string$c=" + address_sw_replace)
        if err != nil {
            fmt.Println(err)
            return
        }
        fmt.Println(resp)
        defer resp.Body.Close()
        var re = regexp.MustCompile(`<ip>10.0.(\S*?)</ip>`)
        var ip_array_unique_item []string
        for true {
            bs := make([]byte, 1014)
            n, err := resp.Body.Read(bs)
            ip_array := re.FindAllString(string(bs), -1)
            fmt.Println(ip_array)
            for _, v := range ip_array {
                skip := false
                for _, u := range ip_array_unique_item {
                    if v == u {
                        skip = true
                        break
                    }
                }
                if !skip {
                    ip_array_unique_item = append(ip_array_unique_item, v)

                }

            }
            if n == 0 || err != nil {
                break
            }

        }
        var ip_array_unique []string
        for _, v := range ip_array_unique_item {
            model_sw := get_sw_model(v[4 : len(v)-5])
            log.Println(model_sw[:15])
            switch model_sw[:15] {
            case "D-Link DES-1228":
                fmt.Println("D-Link DES-1228_f")
                ip_array_unique = append(ip_array_unique, v[4:len(v)-5])
            case "S2320-28TP-EI-A":
                fmt.Println("2320")
                break
            default:
                fmt.Println("Unknown")
            }
        }
        fmt.Println(ip_array_unique)
        SWD := get_value_sw(ip_array_unique)
        fmt.Println(SWD)
        js_map_sw := make(map[string]map[string]map[string]string)
        //js_map_sw_port := make(map[string]string)
        for _, v := range SWD {
            js_map_sw_room := make(map[string]map[string]string)
            for i := 0; i < 24; i++ {
                if v.pair1status[i] == 2 || v.pair1status[i] == 0 {
                    //fmt.Println(i + 1)
                    js_map_sw_room_port := make(map[string]string)
                    resp, err := http.Get("http://test.ru/cgi-bin/ppo/xml/ertel_xml_reports.p_client_for_port_xml?pr_ip$c=" + v.ipsw + "&pr_port$c=" + strconv.Itoa(i+1))
                    if err != nil {
                        fmt.Println(err)
                        return
                    }
                    defer resp.Body.Close()
                    var re = regexp.MustCompile(`<f_office>(\S*?)</f_office>`)
                    for true {
                        bs := make([]byte, 1014)
                        n, err := resp.Body.Read(bs)
                        rooms := re.FindString(string(bs))
                        js_map_sw_room_port["len"] = strconv.Itoa(v.pair1len[i])
                        js_map_sw_room_port["room"] = rooms[10 : len(rooms)-11]
                        js_map_sw_room[strconv.Itoa(i+1)] = js_map_sw_room_port
                        if n == 0 || err != nil {
                            break
                        }

                    }
                    break
                }
                //js_map_sw_port["pair1statusport"+strconv.Itoa(i+1)] = strconv.Itoa(v.pair1status[i])

            }
            js_map_sw[v.ipsw] = js_map_sw_room
        }
        c, _ := json.Marshal(js_map_sw)
        fmt.Println(js_map_sw)
        w.Header().Set("Content-Type", "text/html; charset=utf-8")
        w.Header().Set("Access-Control-Allow-Origin", "*")
        w.Write(c)
    }

}

func get_value_sw(ip_array_unique []string) []SwitchStruct {
    var wg sync.WaitGroup

    f, err := os.OpenFile("testlogfile", os.O_RDWR|os.O_CREATE|os.O_APPEND, 0666)
    if err != nil {
        log.Fatalf("error opening file: %v", err)
    }
    defer f.Close()
    log.SetOutput(f)
    mu := &sync.Mutex{}
    swips := ip_array_unique
    log.Println(swips)
    SWData := make([]SwitchStruct, len(swips))

    for i, ip := range swips {
        SWData[i] = SwitchStruct{ip, make([]int, 24), make([]int, 24), make([]int, 24)}
    }
    wg.Add(len(swips))
    for i := 0; i < len(swips); i++ {
        log.Println(SWData)
        go snmpget(SWData[i], mu, &wg)
    }
    wg.Wait()
    return SWData
}

func snmpget(SWData SwitchStruct, mu *sync.Mutex, wg *sync.WaitGroup) SwitchStruct {
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
        Community: "<SNMP_PASSWORD>",
        Version:   g.Version2c,
        Timeout:   time.Duration(2) * time.Second,
        Logger:    log.New(os.Stdout, "", 0),
    }
    err := params.Connect()

    if err != nil {
        log.Println("Get() err: %v", err)
        return SWData
    }
    defer params.Conn.Close()

    oids := []string{"1.3.6.1.2.1.2.2.1.8"}
    result2, err2 := params.GetBulk(oids, 0, 24)
    if err2 != nil {
        log.Println("Get() err: %v", err2)
        return SWData
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
                return SWData
            }
        }
    }

    oids = []string{"1.3.6.1.4.1.171.12.58.1.1.1.4", "1.3.6.1.4.1.171.12.58.1.1.1.8"}
    result, err2 := params.GetBulk(oids, 0, 24)
    if err2 != nil {
        log.Println("Get() err: %v", err2)
        return SWData
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
        mu.Lock()
        SWData.pair1len[j] = result.Variables[i].Value.(int)
        mu.Unlock()
        j++
    }

    wg.Done()
    return SWData
}

func get_sw_model(ipsw string) (modelsw string) {
    envTarget := ipsw
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
        Community: "<SNMP_PASSWORD>",
        Version:   g.Version2c,
        Timeout:   time.Duration(2) * time.Second,
        Logger:    log.New(os.Stdout, "", 0),
    }
    err := params.Connect()
    if err != nil {
        log.Fatalf("Connect() err: %v", err)
    }
    defer params.Conn.Close()

    oids := []string{"1.3.6.1.2.1.1.1.0"}
    result, err2 := params.Get(oids)
    if err2 != nil {
        log.Fatalf("Get() err: %v", err2)
    }

    for _, variable := range result.Variables {
        modelsw := (string(variable.Value.([]byte)))
        return modelsw

    }
    return modelsw
}
