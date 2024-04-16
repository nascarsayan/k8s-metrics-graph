package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strconv"
	"strings"
)

type PodResource struct {
	Namespace  string              `json:"namespace"`
	Name       string              `json:"name"`
	Containers []ContainerResource `json:"containers"`
}

type ContainerResource struct {
	Name     string  `json:"name"`
	CPUReq   float64 `json:"cpu_req"`
	CPULimit float64 `json:"cpu_limit"`
	MemReq   float64 `json:"mem_req"`
	MemLimit float64 `json:"mem_limit"`
}

func main() {

	outFile := "pod_resources.csv"
	// get the KUBECONFIG environment variable value
	kubeconfig := os.Getenv("KUBECONFIG")
	if kubeconfig != "" {
		outFile = kubeconfig + "_" + outFile
	}

	cmd := exec.Command("kubectl", "get", "pods", "--all-namespaces", "-o", "json")
	output, err := cmd.Output()
	if err != nil {
		fmt.Println("Error executing kubectl command:", err)
		return
	}

	var podResources []PodResource

	// Unmarshal JSON output
	var pods struct {
		Items []struct {
			Metadata struct {
				Namespace string `json:"namespace"`
				Name      string `json:"name"`
			} `json:"metadata"`
			Spec struct {
				Containers []struct {
					Name      string `json:"name"`
					Resources struct {
						Requests struct {
							CPU    string `json:"cpu"`
							Memory string `json:"memory"`
						} `json:"requests"`
						Limits struct {
							CPU    string `json:"cpu"`
							Memory string `json:"memory"`
						} `json:"limits"`
					} `json:"resources"`
				} `json:"containers"`
			} `json:"spec"`
		} `json:"items"`
	}

	if err := json.Unmarshal(output, &pods); err != nil {
		fmt.Println("Error unmarshaling JSON:", err)
		return
	}

	for _, pod := range pods.Items {
		var containerResources []ContainerResource
		for _, container := range pod.Spec.Containers {
			cpuReq, err := normalizeCPU(container.Resources.Requests.CPU)
			if err != nil {
				fmt.Printf("Error normalizing CPU request: %v\n", err)
			}
			cpuLimit, err := normalizeCPU(container.Resources.Limits.CPU)
			if err != nil {
				fmt.Printf("Error normalizing CPU limit: %v\n", err)
			}
			memReq, err := normalizeMemory(container.Resources.Requests.Memory)
			if err != nil {
				fmt.Printf("Error normalizing memory request: %v\n", err)
			}
			memLimit, err := normalizeMemory(container.Resources.Limits.Memory)
			if err != nil {
				fmt.Printf("Error normalizing memory limit: %v\n", err)
			}

			containerResources = append(containerResources, ContainerResource{
				Name:     container.Name,
				CPUReq:   cpuReq,
				CPULimit: cpuLimit,
				MemReq:   memReq,
				MemLimit: memLimit,
			})
		}

		podResources = append(podResources, PodResource{
			Namespace:  pod.Metadata.Namespace,
			Name:       pod.Metadata.Name,
			Containers: containerResources,
		})
	}

	// Create and open a CSV file for writing
	csvFile, err := os.Create(outFile)
	if err != nil {
		fmt.Println("Error creating CSV file:", err)
		return
	}
	defer csvFile.Close()

	// Create a CSV writer
	csvWriter := csv.NewWriter(csvFile)
	defer csvWriter.Flush()

	// Write CSV header
	header := []string{"Namespace", "Pod Name", "Container Name", "CPU Request (m)", "CPU Limit (m)", "Memory Request (Mi)", "Memory Limit (Mi)"}
	if err := csvWriter.Write(header); err != nil {
		fmt.Println("Error writing CSV header:", err)
		return
	}

	// Write data to CSV
	for _, pod := range podResources {
		for _, container := range pod.Containers {
			csvData := []string{
				pod.Namespace,
				pod.Name,
				container.Name,
				strconv.FormatFloat(container.CPUReq, 'f', -1, 64),
				strconv.FormatFloat(container.CPULimit, 'f', -1, 64),
				strconv.FormatFloat(container.MemReq, 'f', -1, 64),
				strconv.FormatFloat(container.MemLimit, 'f', -1, 64),
			}
			if err := csvWriter.Write(csvData); err != nil {
				fmt.Println("Error writing CSV data:", err)
				return
			}
		}
	}

	fmt.Printf("Resource data saved to %s\n", outFile)
}

func normalizeCPU(resourceValue string) (float64, error) {
	if resourceValue == "" {
		return 0, nil
	}
	pattern := `^(\d+(?:\.\d+)?)\s*([a-z]*)$`
	r := regexp.MustCompile(pattern)
	match := r.FindStringSubmatch(strings.ToLower(resourceValue))

	if len(match) != 3 {
		return 0, fmt.Errorf("invalid resource value format: %s", resourceValue)
	}

	numericValue, err := strconv.ParseFloat(match[1], 64)
	if err != nil {
		return 0, err
	}

	unit := strings.ToLower(match[2])
	switch unit {
	case "m":
		numericValue *= 1
	case "":
		numericValue *= 1000
	default:
		return 0, fmt.Errorf("unknown unit: %s", unit)
	}

	return numericValue, nil
}

func normalizeMemory(resourceValue string) (float64, error) {
	if resourceValue == "" {
		return 0, nil
	}
	pattern := `^(\d+(?:\.\d+)?)\s*([a-z]*)$`
	r := regexp.MustCompile(pattern)
	match := r.FindStringSubmatch(strings.ToLower(resourceValue))

	if len(match) != 3 {
		return 0, fmt.Errorf("invalid resource value format: %s", resourceValue)
	}

	numericValue, err := strconv.ParseFloat(match[1], 64)
	if err != nil {
		return 0, err
	}

	unit := strings.ToLower(match[2])
	switch unit {
	case "mi":
		numericValue *= 1
	case "gi":
		numericValue *= 1024
	case "ti":
		numericValue *= 1024 * 1024
	default:
		return 0, fmt.Errorf("unknown unit: %s", unit)
	}

	return numericValue, nil
}
